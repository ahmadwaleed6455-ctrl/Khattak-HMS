import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, date
import json
import pandas as pd # Data aur accounts ki calculation ke liye

st.set_page_config(page_title="Khattak HMS", layout="wide", page_icon="🏨")

# ==========================================
# 1. FIREBASE CONNECTION SETUP
# ==========================================
if not firebase_admin._apps:
    key_dict = json.loads(st.secrets["firebase_json"])
    cred = credentials.Certificate(key_dict)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ==========================================
# 2. SIDEBAR MENU NAVIGATION
# ==========================================
st.sidebar.title("🏨 Khattak HMS")
st.sidebar.markdown("---")
menu = st.sidebar.radio("Main Menu", ["🏨 Dashboard & Booking", "💰 Accounts & Reports", "⚙️ Manage Rooms"])

# Data Fetching
rooms_data = {}
for doc in db.collection('Rooms').stream():
    rooms_data[doc.id] = doc.to_dict().get('beds', [False, False, False, False])
room_names = sorted(list(rooms_data.keys()))


# ==========================================
# PAGE 1: DASHBOARD & BOOKING (Floor-wise)
# ==========================================
if menu == "🏨 Dashboard & Booking":
    st.title("🏨 Live Room Status & Booking")
    
    # --- FLOOR-WISE VIEW ---
    st.subheader("📊 Floor Status")
    
    # Kamron ko floors ke hisaab se alag karna
    floors = {}
    for room in room_names:
        # 'Room_101' se '1' nikalna
        try:
            room_num = room.split('_')
            floor_num = room_num + "th Floor" if int(room_num) > 3 else room_num + "st/nd/rd Floor"
        except:
            floor_num = "Other Rooms"
            
        if floor_num not in floors:
            floors[floor_num] = []
        floors[floor_num].append(room)

    # Har floor ko ek expander (box) mein dikhana
    for floor_name in sorted(floors.keys()):
        with st.expander(f"🏢 {floor_name} (Click to open)", expanded=True):
            cols = st.columns(5)
            for i, room in enumerate(floors[floor_name]):
                beds = rooms_data[room]
                with cols[i % 5]:
                    st.markdown(f"**{room.replace('_', ' ')}**")
                    vacant_beds = beds.count(False)
                    
                    if vacant_beds == 4:
                        st.success("🟢 4 Free")
                    elif vacant_beds == 0:
                        st.error("🔴 Full")
                    else:
                        st.warning(f"🟡 {vacant_beds} Free")
                        
                    st.caption("".join(["🛌 " if b else "🛏️ " for b in beds]))

    st.markdown("---")
    
    # --- BOOKING FORM ---
    st.header("📝 New Customer Entry")
    with st.form("booking_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Customer Name *")
            nic = st.text_input("NIC Number *")
            selected_room = st.selectbox("Assign Room", room_names)
            num_people = st.number_input("Number of Persons", min_value=1, max_value=4, value=1)
        with col2:
            days = st.number_input("Number of Days", min_value=1, value=1)
            per_day = st.number_input("Charges per Day (Rs)", min_value=0, value=1000)
            advance = st.number_input("Advance Paid (Rs)", min_value=0, value=0)
            
        total_bill = days * per_day * num_people
        balance = total_bill - advance
        st.info(f"💰 **Total Bill:** Rs {total_bill} | **Remaining Balance:** Rs {balance}")
        
        submit = st.form_submit_button("Confirm Booking")
        
        if submit:
            if name == "" or nic == "":
                st.error("Please enter Name and NIC!")
            else:
                current_beds = rooms_data[selected_room]
                if num_people > current_beds.count(False):
                    st.error(f"Not enough beds in {selected_room}!")
                else:
                    beds_booked = 0
                    for idx in range(4):
                        if current_beds[idx] == False and beds_booked < num_people:
                            current_beds[idx] = True
                            beds_booked += 1
                            
                    db.collection('Rooms').document(selected_room).update({'beds': current_beds})
                    
                    db.collection('Bookings').add({
                        "Date": str(date.today()),
                        "Timestamp": datetime.now(),
                        "Name": name,
                        "NIC": nic,
                        "Room": selected_room,
                        "Persons": num_people,
                        "Days": days,
                        "Total_Bill": total_bill,
                        "Advance_Paid": advance,
                        "Balance_Pending": balance,
                        "Status": "Active"
                    })
                    st.success("✅ Booking Confirmed!")
                    st.rerun()


# ==========================================
# PAGE 2: ACCOUNTS & REPORTS (Hisaab Kitaab)
# ==========================================
elif menu == "💰 Accounts & Reports":
    st.title("💰 Financial Reports & Statements")
    
    # Firebase se Bookings fetch karna
    docs = db.collection('Bookings').stream()
    bookings_list = [doc.to_dict() for doc in docs]
    
    if len(bookings_list) > 0:
        df = pd.DataFrame(bookings_list)
        df['Date'] = pd.to_datetime(df['Date']).dt.date # Date ko sahi format mein karna
        
        # --- DATE FILTERING ---
        st.subheader("📅 Filter by Date")
        col1, col2 = st.columns(2)
        start_date = col1.date_input("From Date", value=pd.to_datetime('today').date())
        end_date = col2.date_input("To Date", value=pd.to_datetime('today').date())
        
        # Filter Data
        mask = (df['Date'] >= start_date) & (df['Date'] <= end_date)
        filtered_df = df.loc[mask]
        
        st.markdown("---")
        
        # --- TOP METRICS (Bade Boxes) ---
        col_a, col_b, col_c = st.columns(3)
        total_revenue = filtered_df['Total_Bill'].sum()
        total_received = filtered_df['Advance_Paid'].sum()
        total_pending = filtered_df['Balance_Pending'].sum()
        
        col_a.metric("💳 Total Generated Bill", f"Rs {total_revenue:,}")
        col_b.metric("💵 Total Cash Received", f"Rs {total_received:,}")
        col_c.metric("⚠️ Pending Balance", f"Rs {total_pending:,}")
        
        # --- DETAILED TABLE ---
        st.subheader("📝 Detailed Transaction Record")
        # Columns ko tarteeb dena
        display_df = filtered_df[['Date', 'Room', 'Name', 'Persons', 'Total_Bill', 'Advance_Paid', 'Balance_Pending']]
        st.dataframe(display_df, use_container_width=True)
        
    else:
        st.info("Abhi tak koi booking nahi hui. Data khali hai.")


# ==========================================
# PAGE 3: MANAGE ROOMS (Manual Add/Remove)
# ==========================================
elif menu == "⚙️ Manage Rooms":
    st.title("⚙️ Room Management")
    
    st.subheader("➕ Add New Room Manualy")
    st.write("Floor series ke hisaab se room number likhein (e.g., 201, 305, 410).")
    
    with st.form("add_room_form", clear_on_submit=True):
        new_room_num = st.number_input("Room Number", min_value=100, max_value=9999, step=1)
        
        if st.form_submit_button("Create Room"):
            room_id = f"Room_{new_room_num}"
            if room_id in room_names:
                st.error("Yeh kamra pehle se majood hai!")
            else:
                db.collection('Rooms').document(room_id).set({'beds': [False, False, False, False]})
                st.success(f"✅ {room_id} has been added successfully!")
                st.rerun()

    # Majooda Kamron ki List
    st.markdown("---")
    st.subheader("📋 Total Active Rooms")
    st.write(f"Total Kamre: **{len(room_names)}**")
    st.write(", ".join([r.replace("Room_", "") for r in room_names]))
