from flask import Flask, render_template, request, redirect, url_for, session, flash
import pyrebase
import os
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore, storage

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
    if request.method == "POST":
        user_name = request.form.get("name")
        contact_number = request.form.get("contact")
        email = request.form.get("email")
        help_type = request.form.get("help-type")
        urgency_level = request.form.get("urgency")
        description = request.form.get("description")

        # Handling file upload
        document = request.files.get("documents")
        document_url = None
        if document:
            blob = bucket.blob(f"help-documents/{document.filename}")
            blob.upload_from_file(document)
            document_url = blob.public_url  # Get public URL of uploaded file

        # Data to insert
        help_data = {
            "user_name": user_name,
            "contact_number": contact_number,
            "email": email,
            "help_type": help_type,
            "urgency_level": urgency_level,
            "description": description,
            "document_url": document_url
        }

        # Insert into Firestore
        db.collection("help-requests").add(help_data)

        flash("Help request submitted successfully!", "success")
        return redirect(url_for("seek_help"))
    return render_template('seek-help.html')

@app.route('/contribute')
def contribute():
    return render_template('contribute.html')

@app.route('/campaigns')
def campaigns():
    return render_template('campaigns.html')

@app.route('/resources')
def resources():
    return render_template('resources.html')

@app.route('/about-us')
def about_us():
    return render_template('about-us.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == '__main__':
    app.run(debug=True)