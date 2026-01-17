from flask import Flask,render_template,redirect, url_for,request, flash,abort,jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, login_user, login_required,
    logout_user, current_user, UserMixin
)
from datetime import date, datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import os
app = Flask(__name__)


app.config["SQLALCHEMY_DATABASE_URI"]="sqlite:///HospitalDB.db"
app.config['SECRET_KEY'] = 'change-this-secret-key'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

#Data class its a row of data
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(120), nullable=False)
    email=db.Column(db.String(120),unique=True, nullable=False)
    passwordwithhash=db.Column(db.String(255), nullable=False)
    role=db.Column(db.String(30), nullable=False)
    active=db.Column(db.Boolean, nullable=True,default=True)
    doctor=db.relationship('Doctor', backref='user',uselist=False)#user->doctor one to one relationship single object
    patient=db.relationship('Patient', backref='user',uselist=False)#user->Patient again a one to one a user can be a doctor or a patient
    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):     # Flask-Login expects this
        return self.active   # use your own column

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)
    def set_p(self,password):
        self.passwordwithhash=generate_password_hash(password)
    def check_p(self,password):
        return check_password_hash(self.passwordwithhash,password)
    def get_id(self):
        return str(self.id)
class Department(db.Model):#This is the department model
    __tablename__='departments'
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(120), nullable=False)
    description=db.Column(db.String(255))
    doctors=db.relationship('Doctor',backref='department',lazy=True)
class Patient(db.Model):#This is the Patient Model it is in a one to one relationship with the user
    __tablename__ = 'patients'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(255))
    appointments = db.relationship('Appointment', backref='patient', lazy=True)
class Appointment(db.Model):#This model connects Patient and doctor its stores the date time status and has a one to one relationship with Treatment
    __tablename__ = 'appointments'
    id = db.Column(db.Integer, primary_key=True)

    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(20), default='Booked')   

    treatment = db.relationship('Treatment', backref='appointment', uselist=False)  
class Doctor(db.Model):#The Doctor is linked with the user stores the department and the specalization 
    __tablename__ = 'doctors'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    specialization = db.Column(db.String(120), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    bio = db.Column(db.String(255))
    appointments = db.relationship('Appointment', backref='doctor', lazy=True)
    avail = db.relationship('DoctorAvail', backref='doctor', lazy=True )    
class Treatment(db.Model):
    __tablename__='treatments'   
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=False)
    diagnosis = db.Column(db.Text)
    prescription = db.Column(db.Text)
    notes = db.Column(db.Text)
class DoctorAvail(db.Model):
    __tablename__ = 'doctor_availability'
    id = db.Column(db.Integer, primary_key=True)

    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False) 
#Flask needs a way to reload a logged in user from a session..it only stores the user id so this function tell Flask how to fetch User info from the database
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id)) 
def role_required(role):
    def decorator(fn):
        @login_required
        def wrapper(*args, **kwargs):
            if current_user.role != role:
                abort(403)
            if not current_user.active:
                flash("Your account is deactivated/blacklisted.", "danger")#Ensures that user is logged in has the correct role and is active
                return redirect(url_for('login'))
            return fn(*args, **kwargs)
        wrapper.__name__ = fn.__name__
        return wrapper
    return decorator 
@app.route('/admin/patient/<int:patient_id>/history')
@role_required('admin')
def admin_patient_history(patient_id):
    pt = Patient.query.get_or_404(patient_id)

    appts = Appointment.query.filter_by(patient_id=pt.id).order_by(Appointment.date).all()
    #can only be accessed by admin gives the patient history by the patient id and is sorted by the date 
    return render_template(
        "admin/patient_history.html",
        pt=pt,
        appts=appts
    )
@app.route('/doctor/patient/<int:patient_id>/history')
@role_required('doctor')
def patient_history_doctor(patient_id):
    pt = Patient.query.get_or_404(patient_id)
    doctor = Doctor.query.filter_by(user_id=current_user.id).first_or_404()
    #Docs are allowed to see the history of the patient with themselves only 
    appts = Appointment.query.filter_by(
        patient_id=pt.id,
        doctor_id=doctor.id
    ).order_by(Appointment.date).all()

    return render_template(
        "doctor/patient_history.html",
        patient=pt,
        doctor=doctor,
        appointments=appts
    )

def add_adminanddeps():#Used to add admins and the departments when the program is run since the admin cant be registered 
    db.create_all()
    admin = User.query.filter_by(role='admin').first()
    if not admin:
        admin = User(
            name="Super Admin",
            email="admin@hms.com",
            role="admin",
            active=True
        )
        admin.set_p("admin1")  
        db.session.add(admin)
        db.session.commit()

    if Department.query.count() == 0:
        deps = [
            Department(name="Neurology", description="Brain related problems"),
            Department(name="Pediatric ", description="HealthCare Related to children"),
            Department(name="Orthopedics", description="Bones and joints"),
        ]
        db.session.add_all(deps)
        db.session.commit()
 


@app.route("/")#default route checks if the user is authenticated if not then just shows the register and login buttons if authenticated it will check the rool and change the nav bar accordingly
def index():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif current_user.role == 'doctor':
            return redirect(url_for('doctor_dashboard'))
        elif current_user.role == 'patient':
            return redirect(url_for('patient_dashboard'))
    departments=Department.query.all()
    return render_template("index.html",departments=departments)
@app.route('/register', methods=['GET', 'POST'])#registration uses GET
def register():

    departments = Department.query.all() #gets all the departments

    if request.method == 'POST':#if the user clicks register the method is POST
        role = request.form.get('role')

        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        if User.query.filter_by(email=email).first():#check if email exists if yes then give the message email has already been registered
            flash("email has already been registered", "danger")
            return redirect(url_for('register'))

        user = User(name=name, email=email, role=role, active=True)#creates the user
        user.set_p(password)#hash password  
        
        db.session.add(user)#save it
        db.session.commit()

        if role == "patient":
            patient = Patient(
                user_id=user.id,
                age=request.form.get('age'),
                gender=request.form.get('gender'),
                phone=request.form.get('phone'),
                address=request.form.get('address'),
            )
            db.session.add(patient)

        elif role == "doctor":
            doctor = Doctor(
                user_id=user.id,
                specialization=request.form.get('specialization'),
                department_id=request.form.get('department_id')
            )
            db.session.add(doctor)

        db.session.commit()
        flash("Registration successful!", "success")
        return redirect(url_for('login'))

    return render_template('auth/register.html', departments=departments)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user and user.check_p(password):
            if not user.active:
                flash("Your account is deactivated/blacklisted.", "danger")
                return redirect(url_for('login'))
            login_user(user)
            flash("Logged in successfully.", "success")
            return redirect(url_for('index'))
        else:
            flash("Invalid credentials.", "danger")
    return render_template('auth/login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged out.", "info")
    return redirect(url_for('index'))

@app.route('/admin/dashboard')
@role_required('admin')
def admin_dashboard():
    doctorcount = Doctor.query.count()
    patientcount = Patient.query.count()
    appcount = Appointment.query.count()

    doctors = Doctor.query.all()
    patients = Patient.query.all()

    upcoming_appointment = Appointment.query.filter(
        Appointment.date >= date.today()
    ).order_by(Appointment.date, Appointment.time).all()

    return render_template(
        'admin/dashboard.html',
        doctorcount=doctorcount,
        patientcount=patientcount,
        appcount=appcount,
        doctors=doctors,
        patients=patients,
        upcoming_appointment=upcoming_appointment
    )

@app.route('/admin/doctor')
@role_required('admin')
def admin_doctor():
    doctors=Doctor.query.all()
    dept=Department.query.all()
    return render_template('admin/doctor.html',doctors=doctors,dept=dept)
@app.route('/admin/doctor/add',methods=['POST'])
@role_required('admin')
def add_doc():
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')
    specialization = request.form.get('specialization')
    department_id = request.form.get('department_id')
    if User.query.filter_by(email=email).first():
        flash("Email exists please try a different email","danger")
        return redirect(url_for('admin_doctor'))
    user=User(name=name,email=email,role='doctor',active=True)
    user.set_p(password)
    db.session.add(user)
    db.session.commit()
    doctor=Doctor(
        user_id=user.id,
        specialization=specialization,
        department_id=int(department_id) if department_id else None
        
    )
    db.session.add(doctor)
    db.session.commit()
    flash("Doctor has been added","success")
    return redirect(url_for('admin_doctor'))
@app.route('/department/<int:dept_id>')
@login_required
def department_details(dept_id):
    dept = Department.query.get_or_404(dept_id)

    # Doctors in this depARtment
    doctors = Doctor.query.filter_by(department_id=dept.id).all()

    return render_template(
        'department/details.html',
        dept=dept,
        doctors=doctors
    )
@app.route('/doctor/appointments/<int:app_id>/complete', methods=['POST'])
@role_required('doctor')
def doctor_mark_complete(app_id):
    ap = Appointment.query.get_or_404(app_id)
    ap.status = "Completed"
    db.session.commit()
    flash("Marked as Completed", "success")
    return redirect(url_for('doctor_dashboard'))
@app.route('/doctor/appointments/<int:app_id>/cancel', methods=['POST'])
@role_required('doctor')
def doctor_cancel_app(app_id):
    ap = Appointment.query.get_or_404(app_id)
    ap.status = "Cancelled"
    db.session.commit()
    flash("Appointment Cancelled", "info")
    return redirect(url_for('doctor_dashboard'))
 
@app.route("/admin/doctor/edit/<int:doctor_id>", methods=["GET", "POST"])
@role_required("admin")
def edit_doc(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    departments = Department.query.all()

    if request.method == "POST":
        doctor.user.name = request.form.get("name")
        doctor.user.email = request.form.get("email")
        doctor.specialization = request.form.get("spec")
        doctor.department_id = request.form.get("department")

        db.session.commit()
        flash("Doctor updated!", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("admin/edit_doctor.html", doctor=doctor, departments=departments)



@app.route('/admin/doctors/<int:doctor_id>/blacklist', methods=['POST'])
@role_required('admin')
def admin_blacklist_doctor(doctor_id):
    doct = Doctor.query.get_or_404(doctor_id)
    doct.user.active = False
    db.session.commit()
    flash("Doctor has been blacklisted.", "warning")
    return redirect(url_for('admin_doctor'))


@app.route('/admin/patients/<int:patient_id>/blacklist', methods=['POST'])
@role_required('admin')
def blacklist_patient(patient_id):
    patient=Patient.query.get(patient_id)
    patient.user.active=False
    db.session.commit()
    flash("Patient has been blacklisted","warning")
    return redirect(url_for('search_patients'))




@app.route('/admin/patients')
@role_required('admin')
def search_patients():
    qr=request.args.get('qr','')
    patient_qr=Patient.query.join(User)
    if qr:
        patient_qr=patient_qr.filter(
            (User.name.like(f'%{qr}%')) |
             (User.email.ilike(f'%{qr}%')) |
            (Patient.phone.ilike(f'%{qr}%'))
        )
    patient=patient_qr.all()
    return render_template('admin/patient.html',patient=patient,qr=qr)

@app.route('/admin/search')
@role_required('admin')
def doctor_search():
    qr = request.args.get('qr', '')
    doct = Doctor.query.join(User).filter(
        (User.name.ilike(f'%{qr}%')) |
        (Doctor.specialization.ilike(f'%{qr}%'))
    ).all()
    patient = Patient.query.join(User).filter(
        (User.name.ilike(f'%{qr}%')) |
        (User.email.ilike(f'%{qr}%'))
    ).all()
    return render_template('admin/search.html', qr=qr, doct=doct, patient=patient)

@app.route('/doctor/dashboard')
@role_required('doctor')
def doctor_dashboard():
    doctor = Doctor.query.filter_by(user_id=current_user.id).first_or_404()
    datetoday=date.today()
    nextwek=datetoday+timedelta(days=7)
    nextapps=Appointment.query.filter(
        Appointment.doctor_id==doctor.id,
         Appointment.date >= datetoday,
        Appointment.date <= nextwek,
        Appointment.status == 'Booked'
    ).order_by(Appointment.date, Appointment.time).all()
    pp={appt.patient for appt in doctor.appointments}
    return render_template('doctor/dashboard.html',doctor=doctor,nextapps=nextapps,pp=pp)

@app.route('/doctor/appointments/<int:appointment_id>', methods=['GET', 'POST'])
@role_required('doctor')
def app_detail_doct(appointment_id):
    doct = Doctor.query.filter_by(user_id=current_user.id).first_or_404()
    apptt = Appointment.query.get_or_404(appointment_id)
    if apptt.doctor_id != doct.id:
        abort(403)
    if request.method == 'POST':
        status = request.form.get('status')
        diagnosis = request.form.get('diagnosis')
        prescription = request.form.get('prescription')
        notes = request.form.get('notes')
        if status in ['Booked', 'Completed', 'Cancelled']:
            apptt.status = status
        if apptt.treatment:
            treatment = apptt.treatment
        else:
            treatment = Treatment(appointment_id=apptt.id)
            db.session.add(treatment)
        treatment.diagnosis = diagnosis
        treatment.prescription = prescription
        treatment.notes = notes
        db.session.commit()
        flash("Appointment updated.", "success")
        return redirect(url_for('doctor_dashboard'))

    return render_template(
        'doctor/appointment_details.html',
        appointment=apptt
    )
@app.route('/doctor/availability', methods=['GET', 'POST'])
@role_required('doctor')
def doctor_availability():
    doctor = Doctor.query.filter_by(user_id=current_user.id).first_or_404()

    MORNING_START = datetime.strptime("08:00", "%H:%M").time()
    MORNING_END   = datetime.strptime("12:00", "%H:%M").time()
    EVENING_START = datetime.strptime("16:00", "%H:%M").time()
    EVENING_END   = datetime.strptime("21:00", "%H:%M").time()

    today = date.today()
    next7 = [today + timedelta(days=i) for i in range(7)]

    if request.method == 'POST':
        # Clear old availability
        DoctorAvail.query.filter(
            DoctorAvail.doctor_id == doctor.id,
            DoctorAvail.date.in_(next7)
        ).delete()

        # Save new availability
        for d in next7:
            if f"morning_{d}" in request.form:
                db.session.add(DoctorAvail(
                    doctor_id=doctor.id,
                    date=d,
                    start_time=MORNING_START,
                    end_time=MORNING_END
                ))

            if f"evening_{d}" in request.form:
                db.session.add(DoctorAvail(
                    doctor_id=doctor.id,
                    date=d,
                    start_time=EVENING_START,
                    end_time=EVENING_END
                ))

        db.session.commit()
        flash("Availability saved!", "success")
        return redirect(url_for('doctor_availability'))

    # Prepare selected slots for UI
    existing_slots = DoctorAvail.query.filter(
        DoctorAvail.doctor_id == doctor.id,
        DoctorAvail.date.in_(next7)
    ).all()

    existing = set()

    for s in existing_slots:
        if s.start_time == MORNING_START:
            existing.add(("morning", s.date))
        else:
            existing.add(("evening", s.date))

    return render_template(
        "doctor/availability.html",
        doctor=doctor,
        days=next7,
        existing=existing
    )


@app.route('/patient/dashboard')
@role_required('patient')
def patient_dashboard():
    pt = Patient.query.filter_by(user_id=current_user.id).first_or_404()
    today = date.today()

    # UPCOMING = future booked appointments only
    upcoming = Appointment.query.filter(
        Appointment.patient_id == pt.id,
        Appointment.date >= today,
        Appointment.status == 'Booked'
    ).order_by(Appointment.date, Appointment.time).all()

    # PAST = completed or cancelled (OR past dates)
    past = Appointment.query.filter(
        Appointment.patient_id == pt.id
    ).filter(
        (Appointment.date < today) | (Appointment.status != 'Booked')
    ).order_by(Appointment.date.desc(), Appointment.time.desc()).all()

    dept = Department.query.all()

    return render_template(
        'patient/dashboard.html',
        patient=pt,
        upcoming_appointments=upcoming,
        past_appointments=past,
        department=dept
    )

@app.route('/patient/profile',methods=['GET','POST'])
@role_required('patient')
def patient_prof():
    pt=Patient.query.filter_by(user_id=current_user.id).first_or_404()
    if request.method == 'POST':
        current_user.name = request.form.get('name')
        pt.age = int(request.form.get('age') or 0) or None
        pt.gender = request.form.get('gender')
        pt.phone = request.form.get('phone')
        pt.address = request.form.get('address')
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for('patient_prof'))
    return render_template('patient/profile.html',pt=pt)
from flask import jsonify

@app.route('/patient/load_slots/<int:doctor_id>')
@role_required('patient')
def load_slots(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)

    today = date.today()
    next_week = today + timedelta(days=7)

    slots = DoctorAvail.query.filter(
        DoctorAvail.doctor_id == doctor.id,
        DoctorAvail.date >= today,
        DoctorAvail.date <= next_week
    ).all()

    # Organize slots by date
    availability = {}
    for d in range(7):
        day = today + timedelta(days=d)
        availability[day] = {"morning": False, "evening": False}

    MORNING_START = "08:00"
    EVENING_START = "16:00"

    for s in slots:
        if s.start_time.strftime("%H:%M") == MORNING_START:
            availability[s.date]["morning"] = True
        if s.start_time.strftime("%H:%M") == EVENING_START:
            availability[s.date]["evening"] = True

    # Format response
    response_days = []
    for dt, av in availability.items():
        response_days.append({
            "date": dt.strftime("%Y-%m-%d"),
            "morning": "08:00-12:00",
            "evening": "16:00-21:00",
            "morning_available": av["morning"],
            "evening_available": av["evening"]
        })

    return jsonify({"days": response_days})
@app.route('/patient/doctor/<int:doctor_id>/availability')
@role_required('patient')
def patient_check_availability(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    return render_template("patient/doctor_availability.html", doctor=doctor)
@app.route('/patient/doctor/<int:doctor_id>/details')
@role_required('patient')
def patient_doctor_details(doctor_id):
    doc = Doctor.query.get_or_404(doctor_id)
    return render_template('patient/doctor_details.html', doctor=doc)

@app.route('/patient/doctors')
@role_required('patient')
def docforpatient():
    spec=request.args.get('specialization','')
    q2=request.args.get('q2','')
    doctor_qr=Doctor.query.join(User)
    if spec:
        doctor_qr=doctor_qr.filter(
            Doctor.specialization.ilike(f'%{spec}%')
        )
    if q2:
        doctor_qr=doctor_qr.filter(User.name.ilike(f'%{q2}%'))
    docs=doctor_qr.all()
    td2=date.today()
    weekaftertoday=td2+timedelta(days=7)
    avail=DoctorAvail.query.filter(
        DoctorAvail.date>=td2,
        DoctorAvail.date<=weekaftertoday
    ).all()
    return render_template('patient/doctors.html',doctors=docs,availability=avail,specialization=spec,q2=q2)
@app.route('/patient/appointments/book', methods=['GET', 'POST'])
@role_required('patient')
def book_appointment():
    pt=Patient.query.filter_by(user_id=current_user.id).first_or_404()
    dts=Doctor.query.join(User).filter(User.active==True).all()
    if request.method=='POST':
        doctor_id=int(request.form.get('doctor_id'))
        date3=request.form.get('date')
        time3=request.form.get('time')
        d = datetime.strptime(date3, '%Y-%m-%d').date()
        t = datetime.strptime(time3, '%H:%M').time()
        exists=Appointment.query.filter_by(doctor_id=doctor_id,date=d,time=t).first()
        if exists:
            flash("Slot Already Booked","danger")
            return redirect(url_for('book_appointment'))
        appt=Appointment(patient_id=pt.id,doctor_id=doctor_id,date=d,time=t,status='Booked')
        db.session.add(appt)
        db.session.commit()
        flash("Appointment has een booked","success")
        return redirect(url_for('patient_dashboard'))

    return render_template(
        'patient/book_appointment.html',
        doctors=dts
    )
    

@app.route('/patient/appointments/<int:appointment_id>/cancel', methods=['POST'])
@role_required('patient')
def cancel_appointment(appointment_id):
    pt=Patient.query.filter_by(user_id=current_user.id).first_or_404()
    appointment=Appointment.query.get_or_404(appointment_id)
    if appointment.patient_id != pt.id:
       abort(403) 
    if appointment.status == 'Completed':
        flash("Cannot be cancelled appointment has been completed","danger")
        return redirect(url_for('patient_dashboard'))
    appointment.status='Cancelled'
    db.session.commit()
    flash("Appointment has been cancelled","info")
    return redirect(url_for('patient_dashboard'))
if __name__ == "__main__":
    with app.app_context():
        add_adminanddeps()  # runs once at startup
    app.run(debug=True)

 