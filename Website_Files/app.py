from flask import Flask, request, jsonify
from flask_cors import CORS
from firebase_admin import credentials, firestore, initialize_app, auth
import os
from datetime import datetime, timedelta
from functools import wraps
import json

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize Firebase Admin
cred = credentials.Certificate("./serviceAccountKey.json")
firebase_app = initialize_app(cred)
db = firestore.client()

# Collections references
users_ref = db.collection('users')
help_requests_ref = db.collection('help-requests')
campaigns_ref = db.collection('campaigns')
donations_ref = db.collection('donations')
experts_ref = db.collection('experts')
resources_ref = db.collection('resources')
notifications_ref = db.collection('notifications')

# Authentication decorator
def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'No authorization header'}), 401
        
        try:
            # Verify Firebase token
            token = auth_header.split(' ')[1]
            decoded_token = auth.verify_id_token(token)
            request.user = decoded_token
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({'error': str(e)}), 401
    
    return decorated_function

# Admin role check decorator
def require_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.user or not request.user.get('admin'):
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    
    return decorated_function

# User Routes
@app.route('/api/users/profile', methods=['GET'])
@require_auth
def get_user_profile():
    try:
        user_id = request.user['uid']
        user_doc = users_ref.document(user_id).get()
        if user_doc.exists:
            return jsonify(user_doc.to_dict()), 200
        return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/profile', methods=['PUT'])
@require_auth
def update_user_profile():
    try:
        user_id = request.user['uid']
        data = request.json
        users_ref.document(user_id).update(data)
        return jsonify({'message': 'Profile updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Help Request Routes
@app.route('/api/help-requests', methods=['POST'])
@require_auth
def create_help_request():
    try:
        data = request.json
        data['userId'] = request.user['uid']
        data['createdAt'] = firestore.SERVER_TIMESTAMP
        data['status'] = 'pending'
        
        help_request_ref = help_requests_ref.document()
        help_request_ref.set(data)
        
        return jsonify({'id': help_request_ref.id, 'message': 'Help request created successfully'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/help-requests', methods=['GET'])
@require_auth
def get_help_requests():
    try:
        user_id = request.user['uid']
        help_requests = help_requests_ref.where('userId', '==', user_id).stream()
        
        result = []
        for doc in help_requests:
            help_request = doc.to_dict()
            help_request['id'] = doc.id
            result.append(help_request)
            
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Campaign Routes
@app.route('/api/campaigns', methods=['GET'])
def get_campaigns():
    try:
        status = request.args.get('status', 'active')
        campaigns = campaigns_ref.where('status', '==', status).stream()
        
        result = []
        for doc in campaigns:
            campaign = doc.to_dict()
            campaign['id'] = doc.id
            result.append(campaign)
            
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/campaigns', methods=['POST'])
@require_auth
@require_admin
def create_campaign():
    try:
        data = request.json
        data['createdBy'] = request.user['uid']
        data['createdAt'] = firestore.SERVER_TIMESTAMP
        data['raisedAmount'] = 0
        
        campaign_ref = campaigns_ref.document()
        campaign_ref.set(data)
        
        return jsonify({'id': campaign_ref.id, 'message': 'Campaign created successfully'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Donation Routes
@app.route('/api/donations', methods=['POST'])
@require_auth
def create_donation():
    try:
        data = request.json
        data['userId'] = request.user['uid']
        data['timestamp'] = firestore.SERVER_TIMESTAMP
        data['status'] = 'pending'
        
        # Create donation document
        donation_ref = donations_ref.document()
        donation_ref.set(data)
        
        # Update campaign raised amount
        campaign_ref = campaigns_ref.document(data['campaignId'])
        campaign_ref.update({
            'raisedAmount': firestore.Increment(data['amount'])
        })
        
        return jsonify({'id': donation_ref.id, 'message': 'Donation created successfully'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Expert Routes
@app.route('/api/experts', methods=['GET'])
def get_experts():
    try:
        experts = experts_ref.where('availability', '==', True).stream()
        
        result = []
        for doc in experts:
            expert = doc.to_dict()
            expert['id'] = doc.id
            result.append(expert)
            
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Resource Routes
@app.route('/api/resources', methods=['GET'])
def get_resources():
    try:
        category = request.args.get('category')
        query = resources_ref
        
        if category:
            query = query.where('category', '==', category)
            
        resources = query.stream()
        result = []
        for doc in resources:
            resource = doc.to_dict()
            resource['id'] = doc.id
            result.append(resource)
            
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Notification Routes
@app.route('/api/notifications', methods=['GET'])
@require_auth
def get_notifications():
    try:
        user_id = request.user['uid']
        notifications = notifications_ref.where('userId', '==', user_id).order_by('timestamp', direction=firestore.Query.DESCENDING).limit(20).stream()
        
        result = []
        for doc in notifications:
            notification = doc.to_dict()
            notification['id'] = doc.id
            result.append(notification)
            
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Import and register blueprints
from admin import admin_bp
app.register_blueprint(admin_bp, url_prefix='/api/admin')

if __name__ == '__main__':
    app.run(debug=True) 