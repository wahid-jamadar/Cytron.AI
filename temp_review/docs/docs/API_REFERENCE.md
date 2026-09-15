# API Reference

## Patient Registration
### POST /api/v1/patient/register
* Description: Register a new patient
* Request Body: {"name": "string", "email": "string", "phone": "string"}
* Response Schema: {"id": "integer", "name": "string", "email": "string"}
* Auth Required: False
* Example Curl: `curl -X POST -H "Content-Type: application/json" -d '{"name": "John Doe", "email": "john@example.com", "phone": "1234567890"}' http://localhost:3000/api/v1/patient/register`

## Get Patient Information
### GET /api/v1/patient/{patient_id}
* Description: Get patient information
* Request Body: None
* Response Schema: {"id": "integer", "name": "string", "email": "string"}
* Auth Required: True
* Example Curl: `curl -X GET -H "Authorization: Bearer <token>" http://localhost:3000/api/v1/patient/1`

## Book Appointment
### POST /api/v1/appointment/book
* Description: Book an appointment
* Request Body: {"patient_id": "integer", "doctor_id": "integer", "date": "string", "time": "string"}
* Response Schema: {"id": "integer", "patient_id": "integer", "doctor_id": "integer", "date": "string", "time": "string"}
* Auth Required: True
* Example Curl: `curl -X POST -H "Content-Type: application/json" -H "Authorization: Bearer <token>" -d '{"patient_id": 1, "doctor_id": 1, "date": "2024-09-16", "time": "10:00"}' http://localhost:3000/api/v1/appointment/book`

## Get Appointment Information
### GET /api/v1/appointment/{appointment_id}
* Description: Get appointment information
* Request Body: None
* Response Schema: {"id": "integer", "patient_id": "integer", "doctor_id": "integer", "date": "string", "time": "string"}
* Auth Required: True
* Example Curl: `curl -X GET -H "Authorization: Bearer <token>" http://localhost:3000/api/v1/appointment/1`

## Generate Bill
### POST /api/v1/billing/generate
* Description: Generate a bill
* Request Body: {"patient_id": "integer", "appointment_id": "integer", "amount": "float"}
* Response Schema: {"id": "integer", "patient_id": "integer", "appointment_id": "integer", "amount": "float"}
* Auth Required: True
* Example Curl: `curl -X POST -H "Content-Type: application/json" -H "Authorization: Bearer <token>" -d '{"patient_id": 1, "appointment_id": 1, "amount": 100.0}' http://localhost:3000/api/v1/billing/generate`

## Login
### POST /api/v1/auth/login
* Description: Login to the system
* Request Body: {"username": "string", "password": "string"}
* Response Schema: {"token": "string"}
* Auth Required: False
* Example Curl: `curl -X POST -H "Content-Type: application/json" -d '{"username": "admin", "password": "password"}' http://localhost:3000/api/v1/auth/login`

## Register User
### POST /api/v1/auth/register
* Description: Register a new user
* Request Body: {"username": "string", "password": "string", "role": "string"}
* Response Schema: {"id": "integer", "username": "string", "role": "string"}
* Auth Required: False
* Example Curl: `curl -X POST -H "Content-Type: application/json" -d '{"username": "newuser", "password": "password", "role": "admin"}' http://localhost:3000/api/v1/auth/register`