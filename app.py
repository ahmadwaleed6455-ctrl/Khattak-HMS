import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, date
import json
import pandas as pd

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

# Fetch Active Rooms Data
rooms_data = {}
for doc in db.collection('Rooms').stream():
    rooms_data[doc.id] = doc.to_dict().get('beds', [False, False, False, False])
room_names = sorted(list(rooms_data.keys()))


# ==========================================
# PAGE 1: DASHBOARD & BOOKING
# ==========================================
if menu == "🏨 Dashboard & Booking":
    st.title("🏨 Live Room Status & Booking")
    
    # --- FLOOR-WISE SCROLLABLE COLUMNS ---
    st.subheader("📊 Floor Status")
    
    # Kamron ko unke Floor ke hisaab se alag karna (e.g., 101 = Floor 1, 205 = Floor 2)
    floors = {}
    for room in room_names:
        try:
            room_num = int(room.split('_'))
            floor_num = room_num // 100
            floor_name = "Ground Floor" if floor_num == 0 else f"Floor {floor_num}"
        except:
            floor_name = "Other"
            
        if floor_name not in floors:
            floors[floor_name] = []
        floors[floor_name].append(room)

    floor_names_sorted = sorted(floors.keys())
    
    # Har floor ke liye ek column banana
    if len(floor_names_sorted) > 0:
        cols = st.columns(len(floor_names_sorted))
        
        for i, floor in enumerate(floor_names_sorted):
            with cols[i]:
                st.markdown(f"### 🏢 {floor}")
                # SCROLLER KA JAADU: height=400 dene se box lamba nahi hoga balki scroll ban jayega!
                with st.container(height=450, border=True):
                    for room in floors[floor]:
                        beds = rooms_data[room]
                        st.markdown(f"**{room.replace('_', ' ')}**")
                        vacant_beds = beds.count(False)
                        
                        if vacant_beds == 4:
                            st.success("🟢 4 Free")
                        elif vacant_beds == 0:
                            st.error("🔴 Full")
                        else:
                            st.warning(f"🟡 {vacant_beds} Free")
                            
                        st.caption("".join(["🛌 " if b else "🛏️ " for b in beds]))
                        st.divider() # Ek line har room ke baad

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
        
        if st.form_submit_button("Confirm Booking"):
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
# PAGE 2: ACCOUNTS & REPORTS
# ==========================================
elif menu == "💰 Accounts & Reports":
    st.title("💰 Financial Reports & Statements")
    
    docs = db.collection('Bookings').stream()
    bookings_list = [doc.to_dict() for doc in docs]
    
    if len(bookings_list) > 0:
        df = pd.DataFrame(bookings_list)
        df['Date'] = pd.to_datetime(df['Date']).dt.date
        
        st.subheader("📅 Filter by Date")
        col1, col2 = st.columns(2)
        start_date = col1.date_input("From Date", value=pd.to_datetime('today').date())
        end_date = col2.date_input("To Date", value=pd.to_datetime('today').date())
        
        mask = (df['Date'] >= start_date) & (df['Date'] <= end_date)
        filtered_df = df.loc[mask]
        
        st.markdown("---")
        
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("💳 Total Generated Bill", f"Rs {filtered_df['Total_Bill'].sum():,}")
        col_b.metric("💵 Total Cash Received", f"Rs {filtered_df['Advance_Paid'].sum():,}")
        col_c.metric("⚠️ Pending Balance", f"Rs {filtered_df['Balance_Pending'].sum():,}")
        
        st.subheader("📝 Detailed Transaction Record")
        st.dataframe(filtered_df[['Date', 'Room', 'Name', 'Persons', 'Total_Bill', 'Advance_Paid', 'Balance_Pending']], use_container_width=True)
    else:
        st.info("Abhi tak koi booking nahi hui. Data khali hai.")


# ==========================================
# PAGE 3: MANAGE ROOMS
# ==========================================
elif menu == "⚙️ Manage Rooms":
    st.title("⚙️ Room Management")
    
    col1, col2 = st.columns(2)
    
    # --- ADD ROOM ---
    with col1:
        st.subheader("➕ Add New Room")
        with st.form("add_room_form", clear_on_submit=True):
            new_room_num = st.number_input("Room Number (e.g., 201)", min_value=100, max_value=9999, step=1)
            
            if st.form_submit_button("Create Room"):
                room_id = f"Room_{new_room_num}"
                if room_id in room_names:
                    st.error("Yeh kamra pehle se majood hai!")
                else:
                    db.collection('Rooms').document(room_id).set({'beds': [False, False, False, False]})
                    st.success(f"✅ {room_id} has been added!")
                    st.rerun()

    # --- DELETE ROOM ---
    with col2:
        st.subheader("🗑️ Delete a Room")
        with st.form("delete_room_form"):
            room_to_delete = st.selectbox("Select Room to Delete", room_names)
            # Ghalati se delete na ho jaye isliye checkbox
            confirm_delete = st.checkbox(f"Yes, I want to permanently delete {room_to_delete}")
            
            if st.form_submit_button("Delete Room"):
                if not confirm_delete:
                    st.warning("Please tick the confirmation box to delete.")
                else:
                    # Safety Check: Kamra khali hona chahiye
                    current_beds = rooms_data[room_to_delete]
                    if True in current_beds:
                        st.error(f"⚠️ App {room_to_delete} ko delete nahi kar sakte kyunke wahan log thehre hue hain!")
                    else:
                        db.collection('Rooms').document(room_to_delete).delete()
                        st.success(f"✅ {room_to_delete} deleted successfully!")
                        st.rerun()

    st.markdown("---")
    st.subheader("📋 Total Active Rooms")
    st.write(f"Total Kamre: **{len(room_names)}**")
    st.write(", ".join([r.replace("Room_", "") for r in room_names]))
