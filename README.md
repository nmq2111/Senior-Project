# 🎓 University Smart Attendance & Access System

A senior project for a smart university attendance and access control system using **RFID**, **Face Recognition**, and **Smart Door Unlocking** powered by **Django**, **PostgreSQL**, and **ESP32 microcontrollers**.

---

## 📌 Features

### 👨‍🎓 Students

- Register & log in
- View assigned courses
- Mark attendance via RFID or face recognition
- View attendance history by course/date
- Scan to access dorms
- Open dorm doors from the app (if authorized)

### 👩‍🏫 Teachers

- Register & log in
- View assigned courses
- Monitor student attendance by course
- Unlock office door from dashboard
- Track office access logs

### 👨‍💼 Admin

- Secure login
- Manage students and teachers
- Add/edit/delete courses and assign teachers
- Register RFID tags
- View all attendance logs
- Remotely unlock doors and monitor access

---

## 🛠 Tech Stack

| Layer                 | Tools                                   |
| --------------------- | --------------------------------------- |
| Backend               | Python, Django                          |
| Database              | PostgreSQL                              |
| Frontend              | HTML, CSS, JavaScript                   |
| Authentication        | JWT (or Django sessions)                |
| Hardware              | ESP32, RC522 RFID, Relay, Electric Lock |
| Face Recognition      | Python + OpenCV + `face_recognition`    |
| Deployment (optional) | Heroku / Render / Firebase Hosting      |

---

## 🔌 Hardware Components

- ESP32 Dev Board
- RC522 RFID Reader + MIFARE Cards
- 5V Relay Module
- 12V Electric Door Lock
- Buzzer + LEDs
- USB to TTL (for ESP32-CAM)
- ESP32-CAM (optional for face recognition)
- Power adapters (5V & 12V)

---

## 🗃️ Database Models

- `User`: roles (student, teacher, admin)
- `Course`: name, assigned teacher
- `Attendance`: course, student, date/time, method
- `RFIDTag`: UID, assigned user
- `AccessLog`: door, user, timestamp, method
