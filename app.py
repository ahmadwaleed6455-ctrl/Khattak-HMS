import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import date

st.set_page_config(page_title="Khattak HMS", layout="wide")

# ==========================================
# 1. FIREBASE CONNECTION SETUP
# ==========================================
# Check karte hain ke app pehle se connect toh nahi hai (Error se bachne ke liye)
if not firebase_admin._apps:
    # Streamlit secrets se chabi uthana
    creds_dict = dict(st.secrets["firebase"])
    cred = credentials.Certificate(creds_dict)
    firebase_admin.initialize_app(cred)

# Database ka access
db = firestore.client()

# ==========================================
# 2. DEFAULT ROOMS SETUP (Pehli Dafa Ke Liye)
# ==========================================
def initialize_rooms():
    rooms_ref = db.collection('Rooms')
    # Agar database khali hai, toh 5 kamre bana do (101 se 105)
    if not list(rooms_ref.limit(1).stream()):
        for i in range(101, 106):
            rooms_ref.document(f'Room_{i}').set({
                'beds': [False, False, False, False]  # False = Vacant, True = Occupied
            })

initialize_rooms()

# Firebase se live kamron ka data mangwana
rooms_data = {}
for doc in db.collection('Rooms').stream():
    rooms_data[doc.id] = doc.to_dict().get('beds', [False, False, False, False])

st.title("🏨 Khattak Hotel Management System")
st.markdown("---")

# ==========================================
# 3. LIVE DASHBOARD (Room Status)
# ==========================================
st.header("📊 Live Room Status")

# Kamron ko line mein dikhane ke liye columns
cols = st.columns(5)
room_names = sorted(list(rooms_data.keys()))

for i, room in enumerate(room_names):
    beds = rooms_data[room]
    with cols[i % 5]:
        st.subheader(room.replace("_", " "))
        vacant_beds = beds.count(False)
        
        if vacant_beds == 4:
            st.success("🟢 4 Beds Free")
        elif vacant_beds == 0:
            st.error("🔴 Fully Booked")
        else:
            st.warning(f"🟡 {vacant_beds} Beds Free")
            
        for bed_idx, is_occupied in enumerate(beds):
            status = "🛌 Occupied" if is_occupied else "🛏️ Vacant"
            st.write(f"Bed {bed_idx + 1}: {status}")

st.markdown("---")

# ==========================================
# 4. NEW CUSTOMER BOOKING FORM
# ==========================================
st.header("📝 New Customer Entry")

with st.form("booking_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    
    with col1:
        name = st.text_input("Customer Name *")
        nic = st.text_input("NIC Number *")
        selected_room = st.selectbox("Assign Room", room_names)
        num_people = st.number_input("Number of Persons (Beds needed)", min_value=1, max_value=4, value=1)
        
    with col2:
        days = st.number_input("Number of Days", min_value=1, value=1)
        per_day = st.number_input("Charges per Day (Rs)", min_value=0, value=1000)
        advance = st.number_input("Advance Paid (Rs)", min_value=0, value=0)
        
    total_bill = days * per_day * num_people
    balance = total_bill - advance
    
    st.info(f"💰 **Total Bill:** Rs {total_bill} | **Remaining Balance:** Rs {balance}")
    
    submit = st.form_submit_button("Confirm Booking & Save Data")
    
    if submit:
        if name == "" or nic == "":
            st.error("Please enter Customer Name and NIC!")
        else:
            current_beds = rooms_data[selected_room]
            available_beds = current_beds.count(False)
            
            if num_people > available_beds:
                st.error(f"Not enough beds! {selected_room.replace('_', ' ')} only has {available_beds} vacant beds.")
            else:
                # 1. Room ke beds ko Occupied (True) karna
                beds_booked = 0
                for idx in range(4):
                    if current_beds[idx] == False and beds_booked < num_people:
                        current_beds[idx] = True
                        beds_booked += 1
                        
                # Database mein room update karna
                db.collection('Rooms').document(selected_room).update({'beds': current_beds})
                
                # 2. Customer ki detail database mein save karna
                booking_data = {
                    "Date": str(date.today()),
                    "Name": name,
                    "NIC": nic,
                    "Room": selected_room,
                    "Beds_Booked": num_people,
                    "Days": days,
                    "Total_Bill": total_bill,
                    "Advance": advance,
                    "Balance": balance,
                    "Status": "Active"
                }
                db.collection('Bookings').add(booking_data)
                
                st.success("✅ Booking Confirmed! Data saved to Firebase.")
                st.rerun() # App ko refresh karega taake naya status nazar aaye
