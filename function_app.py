import azure.functions as func
import logging
import pyodbc
import requests
import json
import os
import random
from decimal import Decimal

app = func.FunctionApp()

# Lista di nomi casuali per i gatti
cat_names = [
    # Classici
    "Amleto", "Artiglio", "Artù", "Arturo", "Baffone", "Birba", "Birillo", "Casimiro", "Cesare", "Charlie",
    "Chicco", "Denver", "Edgar", "Elvis", "Ettore", "Fiocco", "Frodo", "Giggino", "Gino", "Grumpy",
    "Ian", "James", "Joker", "Junior", "Kant", "Klimt", "Kobe", "Lillo", "Liquirizia", "Oscar",
    "Pippo", "Pucci", "Pulce", "Punto", "Red", "Romeo", "Scheggia", "Virgola",
    # Femminili
    "Agostina", "Alice", "Angela", "Asia", "Azzurra", "Batuffolina", "Bella", "Cleopatra", "Coccinella", "Coccolina",
    "Gatta", "Gioia", "Kiki", "Kinkita", "Lady", "Lilly", "Lucy", "Macchietta", "Matilda", "Meba",
    "Meringa", "Molly", "Nala", "Nerina", "Petra", "Principessa", "Priscilla", "Rose", "Senna", "Sissy",
    "Stella", "Tabata", "Trilly", "Wendy", "Xena", "Ziva", "Zuccherina",
    # Cibo
    "Brownie", "Carota", "Chai", "Cheddar", "Chili", "Curry", "Hershey", "Kahlua", "Kiwi", "Mango",
    "Miso", "Nacho", "Pepe", "Popcorn", "Snickers", "Sushi", "Twinkie", "Zucca",
    # Animali
    "Alce", "Corvo", "Drago", "Foxy", "Orca", "Panda", "Puma", "Scimmia", "Tigre",
    # Letterari e dolci
    "Adina", "Amélie", "Amy", "Bambi", "Bella", "Clementina", "Damara", "Lilly", "Luna", "Malinda",
    "Millie", "Mira", "Paoloma", "Rosa", "Talia", "Tullia", "Viola", "Winni",
    # Mitologici
    "Achille", "Apollo", "Calliope", "Diana", "Eros", "Maia", "Ninfa", "Sibilla", "Ulisse", "Zeus"
]

# Connessione al database tramite variabili d'ambiente
def get_db_connection():
    return pyodbc.connect(
        f'DRIVER={{ODBC Driver 17 for SQL Server}};'
        f'SERVER={os.getenv("SERVER")};'
        f'DATABASE={os.getenv("DATABASE")};'
        f'Trusted_Connection={os.getenv("Trusted_Connection")};'
    )

# Ottieni dati del gatto da The Cat API
def fetch_cat_from_api():
    response = requests.get('https://api.thecatapi.com/v1/images/search')
    if response.status_code == 200:
        data = response.json()[0]
        return data['id'], data['url']
    return None, None

# API: Registra un gatto
@app.route(route="register_cat", methods=["POST"])
def register_cat(req: func.HttpRequest) -> func.HttpResponse:
    cat_id, image_url = fetch_cat_from_api()
    name = random.choice(cat_names)

    if cat_id and image_url:
        with get_db_connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                '''MERGE INTO Cats AS target
                   USING (SELECT ? AS CatID) AS source
                   ON target.CatID = source.CatID
                   WHEN NOT MATCHED THEN
                       INSERT (CatID, CatName, ImageURL) VALUES (?, ?, ?);
                ''',
                (cat_id, cat_id, name, image_url)
            )
            conn.commit()
        return func.HttpResponse(
            json.dumps({'message': 'Cat registered successfully!', 'cat_id': cat_id, 'name': name}),
            status_code=201
        )
    return func.HttpResponse(
        json.dumps({'message': 'Failed to fetch cat information from The Cat API.'}),
        status_code=500
    )

# API: Vota un gatto
@app.route(route="vote_cat", methods=["POST"])
def vote_cat(req: func.HttpRequest) -> func.HttpResponse:
    data = req.get_json()
    cat_id, vote = data.get('cat_id'), data.get('vote')
    if not (1 <= vote <= 5):
        return func.HttpResponse(json.dumps({'message': 'Vote must be between 1 and 5.'}), status_code=400)
    with get_db_connection() as conn, conn.cursor() as cursor:
        cursor.execute('INSERT INTO Votes (CatID, Vote) VALUES (?, ?)', (cat_id, vote))
        conn.commit()
    return func.HttpResponse(json.dumps({'message': 'Vote recorded successfully!'}), status_code=201)

# API: Ottieni i gatti con la media voti più alta
@app.route(route="top_cats", methods=["GET"])
def top_cats(req: func.HttpRequest) -> func.HttpResponse:
    with get_db_connection() as conn, conn.cursor() as cursor:
        cursor.execute('''
            SELECT c.CatID, c.CatName, c.ImageURL, AVG(v.Vote) as AverageVote
            FROM Cats c
            JOIN Votes v ON c.CatID = v.CatID
            GROUP BY c.CatID, c.CatName, c.ImageURL
            ORDER BY AverageVote DESC
        ''')
        rows = cursor.fetchall()
        result = [{
            'CatID': row[0],
            'Name': row[1],
            'ImageURL': row[2],
            'AverageVote': float(row[3])
        } for row in rows]
    return func.HttpResponse(json.dumps(result), status_code=200)

# API: Ottieni tutti i cats
@app.route(route="get_cats", methods=["GET"])
def get_cats(req: func.HttpRequest) -> func.HttpResponse:
    with get_db_connection() as conn, conn.cursor() as cursor:
        cursor.execute('''
            SELECT CatID, CatName, ImageURL
            FROM Cats 
        ''')
        rows = cursor.fetchall()
        result = [{
            'CatID': row[0],
            'Name': row[1],
            'ImageURL': row[2]
        }for row in rows]
    return func.HttpResponse(json.dumps(result), status_code=200)
