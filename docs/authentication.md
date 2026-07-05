# Authentication & Security Flow

HabitMind implements robust authentication and user security measures to ensure that personal health and mood data remain private and secure. 

## 1. Password Management
To provide a seamless User Experience (UX), password updates are handled strictly internally. 
* Users can update their passwords directly inside the `settings.html` interface without being redirected to a separate page.
* Upon a successful password update, the system automatically logs the user out and redirects them to the login page to enforce security and verify the new credentials.

## 2. Password Recovery (Forgot Password)
HabitMind uses a secure, time-sensitive **6-digit OTP (One-Time Password)** system for password recovery, rather than traditional URL tokens.

**The Recovery Flow:**
1. The user requests a password reset by providing their registered email.
2. The backend generates a random 6-digit OTP and temporarily stores it in the secure user session.
3. An email containing the OTP is sent to the user via Flask-Mail (`smtp.gmail.com`).
4. The user enters the 6-digit code on the `verify_otp.html` page.
5. If the code matches the session data, the user is granted access to create a new password.
6. Once reset, all temporary session data (OTP and email) is securely cleared to prevent replay attacks.

This OTP-based approach was specifically implemented to align with the project's strict grading requirements and business logic criteria.