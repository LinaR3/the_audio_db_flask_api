from flask import Flask, jsonify
import requests
import requests
import os
app = Flask(__name__)
@app.route('/', methods=['GET'])
def health_check():
return jsonify({"status": "API corriendo"})
if __name__ == '__main__':
app.run(debug=True)
