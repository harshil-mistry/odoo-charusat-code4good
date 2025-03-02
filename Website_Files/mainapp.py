from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import pyrebase
import os
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore, storage
from datetime import datetime
import json

load_dotenv()

cred = credentials.Certificate(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
firebase_admin.initialize_app(cred, {
    "storageBucket": "connecto-cec3f.firebasestorage.app"  
})
db = firestore.client()
bucket = storage.bucket()  

firebase_config = {
    "apiKey": os.getenv("API_KEY"),
    "authDomain": os.getenv("AUTH_DOMAIN"),
    "databaseURL": os.getenv("DATABASE_URL"),
    "projectId": os.getenv("PROJECT_ID"),
    "storageBucket": os.getenv("STORAGE_BUCKET"),
    "messagingSenderId": os.getenv("MESSAGING_SENDER_ID"),
    "appId": os.getenv("APP_ID"),
}

firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()

app = Flask(__name__)
app.secret_key = "bruh-i-aint-doing-this-shit"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        action = request.form['action']
        email = request.form["email"]
        password = request.form["password"]
        if action == 'register':
            try:
                name = request.form.get("name")
                contact = request.form["contact"]
                user = auth.create_user_with_email_and_password(email, password)
                user_id = user["localId"]

                db.collection("users").document(user_id).set({
                    "name": name,
                    "email": email,
                    "contact" : contact,
                    "created_at": firestore.SERVER_TIMESTAMP
                })
                flash("Registration successful! Please login to proceed ahead")
                return redirect(url_for("index"))
            except Exception as e:
                error_message = str(e)
                if "EMAIL_EXISTS" in error_message:
                    flash("This email is already in use")
                elif "WEAK_PASSWORD" in error_message:
                    flash("Keep a strong password")
                elif "INVALID_EMAIL" in error_message:
                    flash("Please use a valid email")
                else:
                    flash("Some error occured while registering your account")
        else:
            try:
                user = auth.sign_in_with_email_and_password(email, password)
                session["user"] = user["idToken"]
                session['logged_in'] = True
                flash("Login successful!", "success")
                return redirect(url_for("index"))
            except Exception as e:
                error_message = str(e)
                if "INVALID_PASSWORD" in error_message:
                    flash("Incorrect password")
                elif "EMAIL_NOT_FOUND" in error_message:
                    flash("Email not registered")
                elif "INVALID_EMAIL" in error_message:
                    flash("Invalid email format")
                elif "TOO_MANY_ATTEMPTS_TRY_LATER" in error_message:
                    flash("Too many failed attempts. Try again later")
                else:
                    flash("No account found with provided creddentials")
    return render_template('login.html')

@app.route('/seekhelp', methods=['POST', 'GET'])
def seekhelp():
    
    categories = []
    skills_docs = db.collection("skills").get()
    for doc in skills_docs:
        categories.append(doc.id)        

    return render_template('seek-help.html', categories=categories)


@app.route('/contribute', methods=['GET', 'POST'])
def contribute():
    if request.method == 'POST':
        action = request.form.get("action")
        if action == 'services':
            full_name = request.form.get("name")
            email = request.form.get("email")
            contact = request.form.get("contact")
            location = request.form.get("location")
            category = request.form.get("category")
            description = request.form.get("description")
            k1 = request.form.get("keyword-1")
            k2 = request.form.get("keyword-2")
            k3 = request.form.get("keyword-3")
            k4 = request.form.get("keyword-4")
            k5 = request.form.get("keyword-5")
            keywords = [k1, k2, k3, k4, k5]
            
            expert_ref = db.collection("experts").add({
                "full_name": full_name,
                "email": email,
                "contact": contact,
                "location": location,
                "category": category,
                "description": description,
            })
            
            expert_id = expert_ref[1].id  # Get the document ID of the new expert

            # Reference to the category document in 'skills' collection
            skills_ref = db.collection("skills").document(category)
            keyword_doc = skills_ref.get()
            if not keyword_doc.exists:
                skills_ref.set({"status": "1"})  # Create category with 'status' field
            elif "status" not in keyword_doc.to_dict():
                skills_ref.update({"status": "1"})  # Ensure 'status' is present
            for keyword in keywords:
                keyword_ref = skills_ref.collection(keyword).document("data")
                keyword_doc = keyword_ref.get()

                if keyword_doc.exists:
                    # Append expert_id to the existing list
                    keyword_ref.update({"expert_ids": firestore.ArrayUnion([expert_id])})
                else:
                    # Create a new document with the expert_id list
                    keyword_ref.set({"expert_ids": [expert_id]})
            flash("Your response has been registered, thank you for your contribution!")
            
        elif action=="goods":
            try:
                # Get form data
                goods_data = {
                    'donor_name': request.form.get('donor_name'),
                    'donor_email': request.form.get('donor_email'),
                    'donor_phone': request.form.get('donor_phone'),
                    'donor_address': request.form.get('donor_address'),
                    'item_types': request.form.getlist('item_types[]'),
                    'item_description': request.form.get('item_description'),
                    'pickup_preference': request.form.get('pickup_preference'),
                    'preferred_date': request.form.get('preferred_date'),
                    'additional_notes': request.form.get('additional_notes'),
                    'timestamp': datetime.now(),
                    'status': 'pending'  # Initial status
                }

                # Add to Firestore
                db.collection('goods-donation').add(goods_data)

                # Flash success message
                flash('Thank you! Your goods donation information has been submitted successfully. We will contact you soon.', 'success')
                return redirect(url_for('contribute'))

            except Exception as e:
                print(f"Error: {e}")  # For debugging
                flash('There was an error processing your donation. Please try again.', 'error')
                return redirect(url_for('contribute'))
    return render_template('contribute.html')

@app.route('/get_keywords', methods=['GET'])
def get_keywords():
    category = request.args.get('category')
    
    if not category:
        return jsonify({"error": "Category is required"}), 400

    category_ref = db.collection("skills").document(category)

    # Get subcollections under the category (keywords)
    subcollections = [sub.id for sub in category_ref.collections()]

    return jsonify({"keywords": subcollections})


@app.route('/campaigns')
def campaigns():
    return render_template('campaigns.html')

@app.route('/experts')
def experts():
    return render_template('experts.html')

@app.route('/resources')
def resources():
    return render_template('resources.html')

@app.route('/about-us')
def about_us():
    return render_template('about-us.html')

@app.route('/donate', methods=['GET', 'POST'])
def donate():
    if request.method == 'POST':
        try:
            # Basic donation data
            data = {
                'payment_id': request.form.get('payment_id'),
                'amount_inr': int(request.form.get('amount')) / 100,
                'is_anonymous': request.form.get('is_anonymous') == 'true',
                'timestamp': firestore.SERVER_TIMESTAMP
            }

            # Add donor info if not anonymous
            if not data['is_anonymous']:
                data['donor'] = {
                    'first_name': request.form.get('first_name'),
                    'last_name': request.form.get('last_name'),
                    'email': request.form.get('email'),
                    'phone': request.form.get('phone')
                }

            # Store in Firebase
            db.collection('donations').add(data)
            return 'success'

        except Exception as e:
            print(f"Error processing donation: {str(e)}")
            return 'error', 500

    return render_template('donate.html')

@app.route('/experts/<id>')
def expert_profile(id):
    template = f"experts/{id}.html"
    return render_template(template)

@app.route('/submit_help_request', methods=['POST'])
def submit_help_request():
    try:
        # Get form data
        form_data = request.form
        selected_keywords = json.loads(form_data.get('selected_keywords', '[]'))
        
        # Initialize Firestore client
        db = firestore.client()
        
        # Store the help request in Firestore
        help_request = {
            'name': form_data.get('name'),
            'email': form_data.get('email'),
            'contact': form_data.get('contact'),
            'help_type': form_data.get('help-type'),
            'description': form_data.get('description'),
            'keywords': selected_keywords,
            'timestamp': firestore.SERVER_TIMESTAMP
        }
        
        # Add the help request to Firestore
        request_ref = db.collection('help_requests').add(help_request)
        request_id = request_ref[1].id
        
        return jsonify({
            'success': True,
            'request_id': request_id
        })
        
    except Exception as e:
        print(f"Error submitting help request: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/matching_experts/<request_id>')
def matching_experts(request_id):
    try:
        db = firestore.client()
        
        # Get the help request details
        help_request = db.collection('help_requests').document(request_id).get()
        if not help_request.exists:
            return "Request not found", 404
            
        help_request_data = help_request.to_dict()
        selected_keywords = help_request_data.get('keywords', [])
        print(selected_keywords)
        
        # Get expert IDs for all selected keywords
        expert_ids = set()
        for keyword in selected_keywords:
            # Get expert IDs for each keyword
            keywords_ref = db.collection('skills').document(help_request_data['help_type']).collection('keywords').document(keyword).get()
            if keywords_ref.exists:
                keyword_data = keywords_ref.to_dict()
                if 'expert_ids' in keyword_data:
                    expert_ids.update(keyword_data['expert_ids'])
                    
        print(expert_ids)
        
        # Get expert details
        experts = []
        for expert_id in expert_ids:
            expert_doc = db.collection('experts').document(expert_id).get()
            if expert_doc.exists:
                expert_data = expert_doc.to_dict()
                expert_data['id'] = expert_doc.id
                experts.append(expert_data)
        
        return render_template('matching_experts.html', experts=experts)
        
    except Exception as e:
        print(f"Error getting matching experts: {e}")
        return "An error occurred", 500

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == '__main__':
    app.run(debug=True)