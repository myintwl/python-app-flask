#api/v1/details with 's'
#api/v1/healths with 's'
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/api/v1/details', methods=['GET'])
def get_details():
    return jsonify({"message": "Hello World"})

@app.route('/api/v1/healths', methods=['GET'])
def get_healths():
    return jsonify({"message": "Healths endpoint"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)