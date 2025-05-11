# Welcome to Cloud Functions for Firebase for Python!
import os
from firebase_functions import https_fn
from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, firestore, initialize_app

firebase_initialized = False
db = None

def init_firestore():
    global firebase_initialized, db
    if not firebase_initialized:
        cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        firebase_initialized = True

def add_user_to_firestore(user_data, collection='users'):
    """Add user data to Firestore."""
    try:
        # Use UID as document ID for easy retrieval
        doc_ref = db.collection(collection).document(user_data['uid'])
        doc_ref.set(user_data)
        return {"success": True, "message": f"Data added successfully to {collection}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# Create HTTP function for adding user profiles
@https_fn.on_request()
def add_user_profile(req: https_fn.Request) -> https_fn.Response:
    """API to add a user profile to Firestore."""
    try:
        user_data = req.get_json()
        if not user_data or 'uid' not in user_data:
            return jsonify({"success": False, "error": "Invalid user data"}), 400
            
        response = add_user_to_firestore(user_data)
        return jsonify(response)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Create HTTP function for adding business profiles
@https_fn.on_request()
def add_business_profile(req: https_fn.Request) -> https_fn.Response:
    """API to add a business profile to Firestore."""
    try:
        business_data = req.get_json()
        if not business_data or 'uid' not in business_data:
            return jsonify({"success": False, "error": "Invalid business data"}), 400
            
        # Don't allow overriding verification status through this endpoint
        if 'verified' in business_data:
            del business_data['verified']
            
        response = add_user_to_firestore(business_data, collection='businesses')
        return jsonify(response)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Create HTTP function for adding stint postings
@https_fn.on_request()
def add_stint_posting(req: https_fn.Request) -> https_fn.Response:
    """API to add a stint posting to Firestore."""
    try:
        stint_data = req.get_json()
        if not stint_data or 'businessId' not in stint_data:
            return jsonify({"success": False, "error": "Invalid stint data"}), 400
        
        # Check if business is verified
        business_ref = db.collection('businesses').document(stint_data['businessId'])
        business_doc = business_ref.get()
        
        if not business_doc.exists:
            return jsonify({"success": False, "error": "Business not found"}), 404
            
        business_data = business_doc.to_dict()
        if not business_data.get('verified', False):
            return jsonify({"success": False, "error": "Business is not verified"}), 403
            
        # Generate a new document ID for the stint
        stint_ref = db.collection('stints').document()
        stint_data['stintId'] = stint_ref.id
        stint_ref.set(stint_data)
        
        return jsonify({"success": True, "message": "Stint posting added successfully", "stintId": stint_ref.id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Create HTTP function for handling applications
@https_fn.on_request()
def handle_application(req: https_fn.Request) -> https_fn.Response:
    """API to handle job applications."""
    try:
        application_data = req.get_json()
        if not application_data or 'userId' not in application_data or 'stintId' not in application_data:
            return jsonify({"success": False, "error": "Invalid application data"}), 400
            
        # Add application to Firestore
        app_ref = db.collection('applications').document()
        application_data['applicationId'] = app_ref.id
        app_ref.set(application_data)
        
        return jsonify({"success": True, "message": "Application submitted successfully", "applicationId": app_ref.id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Create HTTP function for business verification
@https_fn.on_request()
def verify_business(req: https_fn.Request) -> https_fn.Response:
    """API to verify a business (admin only)."""
    try:
        # Get request data
        data = req.get_json()
        if not data or 'businessId' not in data or 'adminId' not in data:
            return jsonify({"success": False, "error": "Invalid request data"}), 400
            
        business_id = data['businessId']
        admin_id = data['adminId']
        
        # Check if the user is an admin
        admin_ref = db.collection('admins').document(admin_id)
        admin_doc = admin_ref.get()
        
        if not admin_doc.exists:
            return jsonify({"success": False, "error": "Unauthorized: Not an admin"}), 403
            
        # Update business verification status
        business_ref = db.collection('businesses').document(business_id)
        business_ref.update({
            'verified': True,
            'verifiedAt': firestore.SERVER_TIMESTAMP,
            'verifiedBy': admin_id
        })
        
        return jsonify({"success": True, "message": "Business verified successfully"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Create HTTP function for requesting business verification
@https_fn.on_request()
def request_verification(req: https_fn.Request) -> https_fn.Response:
    """API to request business verification."""
    try:
        data = req.get_json()
        if not data or 'businessId' not in data:
            return jsonify({"success": False, "error": "Invalid request data"}), 400
            
        business_id = data['businessId']
        
        # Update business verification request status
        business_ref = db.collection('businesses').document(business_id)
        business_ref.update({
            'verificationRequested': True,
            'verificationRequestedAt': firestore.SERVER_TIMESTAMP
        })
        
        return jsonify({"success": True, "message": "Verification requested successfully"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Create HTTP function to check if a user is an admin
@https_fn.on_request()
def check_admin(req: https_fn.Request) -> https_fn.Response:
    """API to check if a user is an admin."""
    try:
        data = req.get_json()
        if not data or 'userId' not in data:
            return jsonify({"success": False, "error": "Invalid request data"}), 400
            
        user_id = data['userId']
        
        # Check if the user is an admin
        admin_ref = db.collection('admins').document(user_id)
        admin_doc = admin_ref.get()
        
        is_admin = admin_doc.exists
        
        return jsonify({"success": True, "isAdmin": is_admin})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500