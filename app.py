import os

from flask import Flask, render_template, request, jsonify, redirect, url_for
import numpy as np
import pandas as pd
import json
import time
import requests
import io
from zipfile import ZipFile
from flask_cors import CORS
from models import create_todo, get_todos, get_todo_by_id, update_todo_by_id, delete_todo_by_id, search_todos

import sys
import geopandas as gpd
import matplotlib.pyplot as plt
import shapely.speedups
from shapely.geometry import shape, Point, LineString
from sklearn.cluster import DBSCAN
from sklearn.cluster import KMeans
from sklearn import metrics
from sklearn.datasets import make_blobs
from sklearn.preprocessing import StandardScaler
import random
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import datetime


app = Flask(__name__)
CORS(app)

uploaded_inputfile = None
uploaded_inputfile_content = None
uploaded_json_result = None
uploaded_json_result_content = None
uploaded_vehicle_num = None
data_for_frontend = None


@app.route("/optimize_routing", methods=["GET", "POST"])
def optimize_routing():

    global uploaded_inputfile, uploaded_inputfile_content, uploaded_json_result, uploaded_json_result_content, uploaded_vehicle_num, data_for_frontend

    if request.method == "POST":
        # Mendapatkan file input dari form
        uploaded_inputfile = request.files["inputfile"]
        uploaded_inputfile_content = uploaded_inputfile.read()

        uploaded_json_result = request.files["json_result"]
        if uploaded_json_result:
            uploaded_json_result_content = uploaded_json_result.read()

        # Mendapatkan parameter dari form
        uploaded_vehicle_num = request.form["vehicle_num"]

        # Melakukan proses optimasi routing menggunakan fungsi test()
        result = test(uploaded_inputfile_content, uploaded_json_result_content, uploaded_vehicle_num)

        if result:
            data_for_frontend = result

            # Menyimpan data driver baru ke dalam file JSON
            new_driver = {
                "vehicle_num": uploaded_vehicle_num,
                "result": result
            }
            add_new_driver_to_json(new_driver)

            return jsonify(result)
        else:
            return jsonify({'error': 'Failed to optimize routing.'})
    else:
        if data_for_frontend:
            return jsonify(data_for_frontend)
        else:
            return jsonify({'error': 'No data available.'})

def add_new_driver_to_json(new_driver):
    try:
        with open("data/driver.json", "r") as f:
            drivers_data = json.load(f)
    except FileNotFoundError:
        drivers_data = []

    drivers_data.append(new_driver)

    with open("data/driver.json", "w") as f:
        json.dump(drivers_data, f)


@app.route("/get_driver_data", methods=["GET"])
def get_driver_data():
    try:
        with open("data/driver.json", "r") as f:
            driver_data = json.load(f)
        return jsonify(driver_data)
    except FileNotFoundError:
        return jsonify([])


def split_dataframe(df, chunk_size):
    chunks = list()
    num_chunks = len(df) // chunk_size + 1
    for i in range(num_chunks):
        chunks.append(df[i * chunk_size:(i + 1) * chunk_size])
    return chunks


def create_data_model(inputfile_content, json_result_content, vehicle_num):
    """Stores the data for the problem."""
    df = pd.read_excel(io.BytesIO(inputfile_content))
    stringlonglat = ""
    for i in range(len(df)):
        stringlonglat = stringlonglat + str(df["LON"].iloc[i].round(4)) + "," + str(df["LAT"].iloc[i].round(4)) + ";"
    stringlonglat = stringlonglat.rstrip(';')

    if json_result_content is None:
        data = {}

        url = "https://api.aptaapp.net/super/distancematrix/"
        headers = {'longlat': stringlonglat}
        response = requests.get(url, headers=headers)

        data = json.loads(response.text)
        with open('DM.json', 'w') as json_file:
            json.dump(data, json_file)

        matx = []
        for row in data["durations"]:
            matx.append(row)

        data['distance_matrix'] = matx
        demands = [1] * (len(df))
        data["demands"] = demands
        data['num_vehicles'] = int(vehicle_num)
        data['depot'] = 0

        return data
    else:
        data = json.loads(json_result_content)

        matx = []
        for row in data["durations"]:
            matx.append(row)

        data['distance_matrix'] = matx
        demands = [1] * (len(df))
        data["demands"] = demands
        data['num_vehicles'] = int(vehicle_num)
        data['depot'] = 0

        return data


def print_solution(data, manager, routing, solution):
    try:
        result = {}
        result['routes'] = []
        total_distance = 0
        total_load = 0

        for vehicle_id in range(data['num_vehicles']):
            index = routing.Start(vehicle_id)
            route_distance = 0
            route_load = 0
            route = []

            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                route_load += data['demands'][node_index]
                route.append(node_index)
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                route_distance += routing.GetArcCostForVehicle(previous_index, index, vehicle_id)

            route.append(manager.IndexToNode(index))
            route_duration = round(route_distance / 60)

            result['routes'].append({
                'vehicle_id': vehicle_id + 1,
                'route': route,
                'distance': route_distance,
                'duration': route_duration
            })

            total_distance += route_distance
            total_load += route_load

        result['total_distance'] = total_distance
        result['total_duration'] = round(total_distance / 60)

        return result

    except:
        return None


def test(inputfile_content, json_result_content, vehicle_num):
    """Solve the CVRP problem."""
    data = create_data_model(inputfile_content, json_result_content, vehicle_num)
    manager = pywrapcp.RoutingIndexManager(len(data['distance_matrix']),
                                           data['num_vehicles'], data['depot'])
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return data['distance_matrix'][from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    dimension_name = 'Distance'
    routing.AddDimension(
        transit_callback_index,
        0,
        32400,
        True,
        dimension_name)
    distance_dimension = routing.GetDimensionOrDie(dimension_name)
    distance_dimension.SetGlobalSpanCostCoefficient(100)

    def demand_callback(from_index):
        from_node = manager.IndexToNode(from_index)
        return data['demands'][from_node]

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
    search_parameters.time_limit.FromSeconds(100)

    solution = routing.SolveWithParameters(search_parameters)

    if solution:
        result = print_solution(data, manager, routing, solution)

        if result:
            return result

    return None


# crud table crud

def format_todo(drivers):
    return [{
        'id': driver['id'],
        'no': driver['no'],
        'name': driver['name'],
        'loc_25': driver['loc_25'],
        'lat': driver['lat'],
        'lon': driver['lon'],
        'date': driver['date']
    } for driver in drivers]

@app.route('/todos', methods=['GET'])
def get_todos_route():
    todos = get_todos()
    new_todo = format_todo(todos)
    return jsonify(new_todo), 200

@app.route('/todos', methods=['POST'])
def create_todo_route():
    data = request.get_json()
    no = data['no']
    name = data['name']
    loc_25 = data['loc_25']
    lat = data['lat']
    lon = data['lon']
    create_todo(no, name, loc_25, lat, lon)
    return jsonify({'message': 'Driver created successfully'}), 201

@app.route('/todos/<int:id>', methods=['GET'])
def get_todo_route(id):
    todo = get_todo_by_id(id)
    new_todo = format_todo([todo])
    return jsonify(new_todo), 200

@app.route('/todos/<int:id>', methods=['PUT'])
def update_todo_route(id):
    data = request.get_json()
    no = data['no']
    name = data['name']
    loc_25 = data['loc_25']
    lat = data['lat']
    lon = data['lon']
    update_todo_by_id(id, no, name, loc_25, lat, lon)
    return jsonify({'message': 'Todo updated successfully'}), 200

@app.route('/todos/<int:id>', methods=['DELETE'])
def delete_todo_route(id):
    delete_todo_by_id(id)
    return jsonify({'message': 'Todo deleted successfully'}), 200

@app.route('/todos/search/<search>', methods=['GET'])
def search_todo_route(search):
    todos = search_todos(search)
    new_todo = format_todo(todos)
    return jsonify(new_todo), 200


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8080))
    app.run(port=port, host='0.0.0.0')
