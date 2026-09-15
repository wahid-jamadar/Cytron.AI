
from models.patient import Patient
from models.doctor import Doctor
from models.appointment import Appointment
from models.bill import Bill
from models.pharmacy_item import PharmacyItem
from models.laboratory_test import LaboratoryTest
from models.medical_record import MedicalRecord
from models.staff import Staff
from database import SessionLocal

def seed_data():
    db = SessionLocal()

    patient = Patient(name='John Doe', email='john@example.com', phone='1234567890')
    db.add(patient)
    db.commit()

    doctor = Doctor(name='Jane Doe', email='jane@example.com', phone='1234567890')
    db.add(doctor)
    db.commit()

    appointment = Appointment(patient_id=patient.id, doctor_id=doctor.id, date='2024-01-01', time='10:00')
    db.add(appointment)
    db.commit()

    bill = Bill(patient_id=patient.id, appointment_id=appointment.id, amount=100.0)
    db.add(bill)
    db.commit()

    pharmacy_item = PharmacyItem(name='Aspirin', description='Pain reliever', price=10.0)
    db.add(pharmacy_item)
    db.commit()

    laboratory_test = LaboratoryTest(name='Blood test', description='Blood test', price=50.0)
    db.add(laboratory_test)
    db.commit()

    medical_record = MedicalRecord(patient_id=patient.id, description='Patient has a cold')
    db.add(medical_record)
    db.commit()

    staff = Staff(name='Bob Smith', email='bob@example.com', phone='1234567890')
    db.add(staff)
    db.commit()

if __name__ == '__main__':
    seed_data()