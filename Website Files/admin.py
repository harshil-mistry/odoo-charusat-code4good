from flask import Blueprint, request, jsonify
from firebase_admin import firestore
from functools import wraps
from app import require_auth, require_admin, db

admin_bp = Blueprint('admin', __name__)

# Collection references
users_ref = db.collection('users')
help_requests_ref = db.collection('help_requests')
campaigns_ref = db.collection('campaigns')
donations_ref = db.collection('donations')
experts_ref = db.collection('experts')
resources_ref = db.collection('resources')

# Admin Dashboard Stats
@admin_bp.route('/stats', methods=['GET'])
@require_auth
@require_admin
def get_admin_stats():
    try:
        # Get total users
        users_count = len(list(users_ref.stream()))
        
        # Get pending help requests
        pending_requests = len(list(help_requests_ref.where('status', '==', 'pending').stream()))
        
        # Get active campaigns
        active_campaigns = len(list(campaigns_ref.where('status', '==', 'active').stream()))
        
        # Get total donations
        donations = donations_ref.stream()
        total_donations = sum(doc.to_dict()['amount'] for doc in donations)
        
        return jsonify({
            'total_users': users_count,
            'pending_requests': pending_requests,
            'active_campaigns': active_campaigns,
            'total_donations': total_donations
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# User Management
@admin_bp.route('/users', methods=['GET'])
@require_auth
@require_admin
def get_all_users():
    try:
        users = users_ref.stream()
        result = []
        for doc in users:
            user = doc.to_dict()
            user['id'] = doc.id
            result.append(user)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/users/<user_id>', methods=['PUT'])
@require_auth
@require_admin
def update_user(user_id):
    try:
        data = request.json
        users_ref.document(user_id).update(data)
        return jsonify({'message': 'User updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Help Request Management
@admin_bp.route('/help-requests', methods=['GET'])
@require_auth
@require_admin
def get_all_help_requests():
    try:
        status = request.args.get('status')
        query = help_requests_ref
        
        if status:
            query = query.where('status', '==', status)
            
        help_requests = query.stream()
        result = []
        for doc in help_requests:
            help_request = doc.to_dict()
            help_request['id'] = doc.id
            result.append(help_request)
            
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/help-requests/<request_id>', methods=['PUT'])
@require_auth
@require_admin
def update_help_request(request_id):
    try:
        data = request.json
        help_requests_ref.document(request_id).update(data)
        
        # Create notification for user
        if 'status' in data:
            help_request = help_requests_ref.document(request_id).get()
            user_id = help_request.to_dict()['userId']
            
            notification_data = {
                'userId': user_id,
                'type': 'help_request_update',
                'title': 'Help Request Update',
                'message': f'Your help request has been {data["status"]}',
                'read': False,
                'timestamp': firestore.SERVER_TIMESTAMP,
                'relatedId': request_id,
                'relatedType': 'help_request'
            }
            
            db.collection('notifications').add(notification_data)
        
        return jsonify({'message': 'Help request updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Campaign Management
@admin_bp.route('/campaigns', methods=['GET'])
@require_auth
@require_admin
def get_all_campaigns():
    try:
        campaigns = campaigns_ref.stream()
        result = []
        for doc in campaigns:
            campaign = doc.to_dict()
            campaign['id'] = doc.id
            result.append(campaign)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/campaigns/<campaign_id>', methods=['PUT'])
@require_auth
@require_admin
def update_campaign(campaign_id):
    try:
        data = request.json
        campaigns_ref.document(campaign_id).update(data)
        return jsonify({'message': 'Campaign updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/campaigns/<campaign_id>', methods=['DELETE'])
@require_auth
@require_admin
def delete_campaign(campaign_id):
    try:
        campaigns_ref.document(campaign_id).delete()
        return jsonify({'message': 'Campaign deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Expert Management
@admin_bp.route('/experts', methods=['POST'])
@require_auth
@require_admin
def create_expert():
    try:
        data = request.json
        expert_ref = experts_ref.document()
        expert_ref.set(data)
        return jsonify({'id': expert_ref.id, 'message': 'Expert created successfully'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/experts/<expert_id>', methods=['PUT'])
@require_auth
@require_admin
def update_expert(expert_id):
    try:
        data = request.json
        experts_ref.document(expert_id).update(data)
        return jsonify({'message': 'Expert updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Resource Management
@admin_bp.route('/resources', methods=['POST'])
@require_auth
@require_admin
def create_resource():
    try:
        data = request.json
        data['addedBy'] = request.user['uid']
        data['createdAt'] = firestore.SERVER_TIMESTAMP
        
        resource_ref = resources_ref.document()
        resource_ref.set(data)
        
        return jsonify({'id': resource_ref.id, 'message': 'Resource created successfully'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/resources/<resource_id>', methods=['PUT', 'DELETE'])
@require_auth
@require_admin
def manage_resource(resource_id):
    try:
        if request.method == 'PUT':
            data = request.json
            data['updatedAt'] = firestore.SERVER_TIMESTAMP
            resources_ref.document(resource_id).update(data)
            return jsonify({'message': 'Resource updated successfully'}), 200
        else:
            resources_ref.document(resource_id).delete()
            return jsonify({'message': 'Resource deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Analytics
@admin_bp.route('/analytics', methods=['GET'])
@require_auth
@require_admin
def get_analytics():
    try:
        # Get user growth
        users = users_ref.order_by('createdAt').stream()
        user_growth = []
        for user in users:
            user_data = user.to_dict()
            user_growth.append({
                'timestamp': user_data['createdAt'],
                'total': len(user_growth) + 1
            })
            
        # Get donation statistics
        donations = donations_ref.where('status', '==', 'completed').stream()
        donation_stats = {
            'total_amount': 0,
            'count': 0,
            'average': 0
        }
        
        for donation in donations:
            donation_data = donation.to_dict()
            donation_stats['total_amount'] += donation_data['amount']
            donation_stats['count'] += 1
            
        if donation_stats['count'] > 0:
            donation_stats['average'] = donation_stats['total_amount'] / donation_stats['count']
            
        return jsonify({
            'user_growth': user_growth,
            'donation_stats': donation_stats
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500 