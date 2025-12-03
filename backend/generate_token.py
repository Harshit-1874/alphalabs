import jwt
import datetime
import sys

def generate_test_token(user_id="user_test123", email="test@example.com", name="Test User"):
    """
    Generates a dummy JWT token for testing purposes.
    This token is signed with a dummy secret ('secret') which matches the 
    fallback logic in auth.py when CLERK_SECRET_KEY is not set or verification fails.
    """
    
    payload = {
        "sub": user_id,
        "email": email,
        "first_name": name.split(" ")[0],
        "last_name": name.split(" ")[1] if " " in name else "",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=1),
        "iat": datetime.datetime.utcnow()
    }
    
    # Using HS256 algorithm and 'secret' key as per the fallback in auth.py
    token = jwt.encode(payload, "secret", algorithm="HS256")
    return token

if __name__ == "__main__":
    # Allow command line args: python generate_token.py [user_id] [email]
    uid = sys.argv[1] if len(sys.argv) > 1 else "user_test123"
    email = sys.argv[2] if len(sys.argv) > 2 else "test@example.com"
    
    token = generate_test_token(uid, email)
    
    print("\n" + "="*60)
    print("🔑 GENERATED TEST TOKEN")
    print("="*60)
    print(f"User ID: {uid}")
    print(f"Email:   {email}")
    print("-" * 60)
    print(token)
    print("="*60 + "\n")
    print("Usage in cURL:")
    print(f"-H 'Authorization: Bearer {token}'")
    print("\n")
