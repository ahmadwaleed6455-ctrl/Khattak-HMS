import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, date
import json
import pandas as pd

st.set_page_config(page_title="Khattak HMS", layout="wide", page_icon="🏨")

# ==========================================
# 0. SECURE LOGIN SYSTEM
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns(3)
    with col2:
        st.title("🔒 Security Lock")
        st.write("Authorized Personnel Only")
        with st.form("login_form"):
            password = st.text_input("Enter Admin Password", type="password")
            if st.form_submit_button("Login"):
                if password == st.secrets["admin_password"]:
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("❌ Incorrect Password!")
else:
    # ==========================================
    # 1. FIREBASE CONNECTION
    # ==========================================
    if not firebase_admin._apps:
        key_dict = json.loads(st.secrets["firebase_json"])
        cred = credentials.Certificate(key_dict)
        firebase_admin.initialize_app(cred)

    db = firestore.client()

    # ==========================================
    # 2. SIDEBAR NAVIGATION
    # ==========================================
    st.sidebar.title("🏨 Khattak HMS")
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()
        
    st.sidebar.markdown("---")
    menu = st.sidebar.radio("Main Menu", [
        "🏨 Dashboard & Booking", 
        "🧾 Invoices & Checkout",  
        "💰 Accounts & Reports", 
        "⚙️ Manage Rooms"
    ])

    rooms_data = {}
    for doc in db.collection('Rooms').stream():
        rooms_data[doc.id] = doc.to_dict().get('beds', [False, False, False, False])
    room_names = sorted(list(rooms_data.keys()))
# ==========================================
    # PAGE 1: DASHBOARD & BOOKING (FIXED 4 COLUMNS WITH SCROLLBAR)
    # ==========================================
    if menu == "🏨 Dashboard & Booking":
        st.title("🏨 Live Room Dashboard")
        
        # 1. Kamron ko unke makhsoos floors mein taqseem karna
        floor_rooms = {1: [], 2: [], 3: [], 4: []}
        
        for room in room_names:
            room_num_str = ''.join([c for c in room if c.isdigit()])
            if room_num_str:
                room_num = int(room_num_str)
                floor_num = room_num // 100
                
                if floor_num < 1: floor_num = 1
                if floor_num > 4: floor_num = 4
                
                floor_rooms[floor_num].append(room)

        # 2. Fix 4 Columns Banana
        col1, col2, col3, col4 = st.columns(4)
        cols = [col1, col2, col3, col4]
        floor_titles = ["1st Floor", "2nd Floor", "3rd Floor", "4th Floor"]
        
        for i in range(4):
            with cols[i]:
                # Khubsurat Floor Heading
                st.markdown(f"<h4 style='text-align: center; background-color: #2c3e50; color: white; padding: 10px; border-radius: 5px; margin-bottom: 10px;'>{floor_titles[i]}</h4>", unsafe_allow_html=True)
                
                sorted_rooms = sorted(floor_rooms[i+1], key=lambda x: int(''.join(filter(str.isdigit, x)) or 0))
                
                if len(sorted_rooms) > 0:
                    # SCROLLER KA JAADU: height=400 lagane se sirf 3 rows dikhengi, uske baad scrollbar aa jayega!
                    with st.container(height=400, border=False):
                        for room in sorted_rooms:
                            beds = rooms_data[room]
                            room_display_num = ''.join([c for c in room if c.isdigit()])
                            vacant_beds = beds.count(False)
                            
                            if vacant_beds == 4:
                                status_text = "🟢 4 Free"
                                status_color = "#28a745"
                            elif vacant_beds == 0:
                                status_text = "🔴 Full"
                                status_color = "#dc3545"
                            else:
                                status_text = f"🟡 {vacant_beds} Free"
                                status_color = "#e6b800"
                                
                            bed_icons = "".join(["🛌 " if b else "🛏️ " for b in beds])
                            
                            st.markdown(f"""
                            <div style="border: 1px solid #ddd; border-left: 6px solid {status_color}; border-radius: 5px; padding: 12px; margin-bottom: 12px; background-color: #fcfcfc; box-shadow: 2px 2px 5px rgba(0,0,0,0.05);">
                                <h3 style="margin: 0; color: #2c3e50; font-size: 22px;">Room {room_display_num}</h3>
                                <p style="margin: 5px 0 2px 0; font-weight: bold; color: {status_color}; font-size: 15px;">{status_text}</p>
                                <p style="margin: 0; font-size: 18px; letter-spacing: 2px;">{bed_icons}</p>
                            </div>
                            """, unsafe_allow_html=True)
                else:
                    st.info("No Rooms")

        st.markdown("---")
        
        # ==========================================
        # BOOKING FORM (Yahan se niche aapka Booking form hoga)
        # ==========================================
        st.header("📝 New Customer Entry")
        # ... (Aapka baqi form ka code) ...
        with st.form("booking_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Customer Name *")
                nic = st.text_input("NIC Number *")
                selected_rooms = st.multiselect("Assign Room(s) *", room_names)
                num_people = st.number_input("Total Number of Persons", min_value=1, max_value=20, value=1)
            with col2:
                days = st.number_input("Number of Days", min_value=1, value=1)
                per_day = st.number_input("Charges per Day (Rs) - (Per Room)", min_value=0, value=1000)
                advance = st.number_input("Advance Paid (Rs)", min_value=0, value=0)
                
            total_bill = days * per_day * len(selected_rooms)
            balance = total_bill - advance
            st.info(f"💰 **Total Bill:** Rs {total_bill} | **Remaining Balance:** Rs {balance}")
            
            if st.form_submit_button("Confirm Booking"):
                if name == "" or nic == "" or not selected_rooms:
                    st.error("Please fill Name, NIC, and select at least one room!")
                else:
                    total_available_beds = sum(rooms_data[r].count(False) for r in selected_rooms)
                    
                    if num_people > total_available_beds:
                        st.error(f"Not enough beds! The selected rooms only have {total_available_beds} free beds.")
                    else:
                        rooms_to_update = {}
                        people_left_to_assign = num_people
                        
                        for r in selected_rooms:
                            beds = rooms_data[r].copy()
                            for idx in range(4):
                                if beds[idx] == False and people_left_to_assign > 0:
                                    beds[idx] = True
                                    people_left_to_assign -= 1
                            rooms_to_update[r] = beds
                                
                        for r, new_beds in rooms_to_update.items():
                            db.collection('Rooms').document(r).update({'beds': new_beds})
                        
                        rooms_str = ", ".join([r.replace("Room_", "") for r in selected_rooms])
                        
                        db.collection('Bookings').add({
                            "Date": str(date.today()),
                            "Timestamp": datetime.now(),
                            "Name": name,
                            "NIC": nic,
                            "Room": rooms_str,
                            "Persons": num_people,
                            "Days": days,
                            "Total_Bill": total_bill,
                            "Advance_Paid": advance,
                            "Balance_Pending": balance,
                            "Status": "Active"
                        })
                        st.success("✅ Booking Confirmed! Go to 'Invoices & Checkout' to manage.")
                        st.rerun()
    # ==========================================
    # PAGE 2: INVOICES & CHECKOUT
    # ==========================================
    elif menu == "🧾 Invoices & Checkout":
        st.title("🧾 Invoice & Room Departure")
        
        bookings = []
        for doc in db.collection('Bookings').stream():
            data = doc.to_dict()
            b = {
                'id': doc.id,
                'Name': data.get('Name', 'Unknown'),
                'NIC': data.get('NIC', 'N/A'),
                'Room': data.get('Room', 'N/A'),
                'Date': data.get('Date', 'N/A'),
                'Persons': data.get('Persons', data.get('Beds_Booked', 1)),
                'Days': data.get('Days', 1),
                'Total_Bill': data.get('Total_Bill', 0),
                'Advance_Paid': data.get('Advance_Paid', data.get('Advance', 0)),
                'Balance_Pending': data.get('Balance_Pending', data.get('Balance', 0)),
                'Status': data.get('Status', 'Active')
            }
            bookings.append(b)
            
        active_bookings = [b for b in bookings if b['Status'] == 'Active']
            
        if not active_bookings:
            st.info("No active customers currently in the hotel.")
        else:
            booking_opts = {b['id']: f"{b['Name']} - Room(s): {b['Room']} | Dues: Rs {b['Balance_Pending']}" for b in active_bookings}
            selected_booking_id = st.selectbox("Search & Select Customer Record", list(booking_opts.keys()), format_func=lambda x: booking_opts[x])
            selected_b = next((b for b in active_bookings if b['id'] == selected_booking_id), None)
            
            if selected_b:
                st.markdown("---")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("💵 Update Payment")
                    st.write(f"**Current Due Balance:** Rs {selected_b['Balance_Pending']}")
                    
                    with st.form("pay_dues_form"):
                        new_payment = st.number_input("Enter Receiving Amount (Rs)", min_value=0, max_value=selected_b['Balance_Pending'], value=selected_b['Balance_Pending'])
                        if st.form_submit_button("Update Payment"):
                            new_advance = selected_b['Advance_Paid'] + new_payment
                            new_balance = selected_b['Total_Bill'] - new_advance
                            
                            db.collection('Bookings').document(selected_booking_id).update({
                                'Advance_Paid': new_advance,
                                'Balance_Pending': new_balance
                            })
                            st.success(f"Payment of Rs {new_payment} updated! Please refresh invoice.")
                            st.rerun()

                    st.markdown("---")
                    st.subheader("🚪 Departure & Check-out")
                    if selected_b['Balance_Pending'] > 0:
                        st.error("⚠️ Customer ka hisaab baqi hai! Please clear the due balance to check out.")
                        st.button("Close Room & Check-out", disabled=True)
                    else:
                        st.success("✅ Payment is cleared. Customer is ready to check out.")
                        if st.button("Complete Check-out & Free Rooms", type="primary"):
                            
                            rooms_list = [f"Room_{r.strip()}" for r in selected_b['Room'].split(",")]
                            people_to_remove = selected_b['Persons']
                            
                            for r in rooms_list:
                                if r in rooms_data:
                                    current_beds = rooms_data[r].copy()
                                    for idx in range(4):
                                        if current_beds[idx] == True and people_to_remove > 0:
                                            current_beds[idx] = False
                                            people_to_remove -= 1
                                    db.collection('Rooms').document(r).update({'beds': current_beds})
                            
                            db.collection('Bookings').document(selected_booking_id).update({
                                'Status': 'Checked Out'
                            })
                            
                            st.success("Departure Successful! Rooms are now Vacant.")
                            st.rerun()

                with col2:
                    st.subheader("🖨️ Customer Invoice")
                    
                    invoice_html = f"""
                    <style>
                        @media print {{
                            .no-print {{ display: none !important; }}
                            body {{ background-color: white !important; }}
                        }}
                    </style>
                    <div style="border: 2px solid #333; padding: 20px; border-radius: 10px; background-color: white; color: black; font-family: Arial, sans-serif;">
                        
                        <div class="no-print" style="text-align: center; margin-bottom: 20px;">
                            <button onclick="window.print()" style="background-color: #2c3e50; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; width: 100%;">🖨️ Print Invoice</button>
                        </div>

                        <div style="text-align: center; border-bottom: 2px dashed #ccc; padding-bottom: 10px; margin-bottom: 20px;">
                            <h2 style="margin: 0; color: #2c3e50;">HOTEL KHATTAK HMS</h2>
                            <p style="margin: 5px 0; font-size: 14px;">Peshawar, Khyber Pakhtunkhwa</p>
                            <p style="margin: 5px 0; font-size: 14px; font-weight: bold;">Date: {selected_b['Date']}</p>
                        </div>
                        
                        <table style="width: 100%; margin-bottom: 20px; border-collapse: collapse;">
                            <tr><td style="padding: 5px 0;"><strong>Customer Name:</strong></td><td style="text-align: right;">{selected_b['Name']}</td></tr>
                            <tr><td style="padding: 5px 0;"><strong>NIC:</strong></td><td style="text-align: right;">{selected_b['NIC']}</td></tr>
                            <tr><td style="padding: 5px 0;"><strong>Room(s):</strong></td><td style="text-align: right;">{selected_b['Room']}</td></tr>
                            <tr><td style="padding: 5px 0;"><strong>Persons:</strong></td><td style="text-align: right;">{selected_b['Persons']}</td></tr>
                            <tr><td style="padding: 5px 0;"><strong>Duration:</strong></td><td style="text-align: right;">{selected_b['Days']} Days</td></tr>
                        </table>
                        
                        <div style="border-top: 2px dashed #ccc; padding-top: 15px;">
                            <table style="width: 100%; font-size: 18px;">
                                <tr><td style="padding: 5px 0;"><strong>Total Bill:</strong></td><td style="text-align: right;">Rs {selected_b['Total_Bill']:,}</td></tr>
                                <tr><td style="padding: 5px 0; color: green;"><strong>Amount Paid:</strong></td><td style="text-align: right; color: green;">Rs {selected_b['Advance_Paid']:,}</td></tr>
                                <tr><td style="padding: 10px 0; font-size: 20px; color: {'red' if selected_b['Balance_Pending'] > 0 else 'black'};"><strong>Balance Due:</strong></td><td style="text-align: right; font-weight: bold; color: {'red' if selected_b['Balance_Pending'] > 0 else 'black'};">Rs {selected_b['Balance_Pending']:,}</td></tr>
                            </table>
                        </div>
                        
                        <div style="text-align: center; margin-top: 30px; font-size: 12px;">
                            <p>Thank you for choosing Hotel Khattak!</p>
                            <p>System Generated Invoice</p>
                        </div>
                    </div>
                    """
                    st.components.v1.html(invoice_html, height=600, scrolling=True)


    # ==========================================
    # PAGE 3: ACCOUNTS & REPORTS
    # ==========================================
    elif menu == "💰 Accounts & Reports":
        st.title("💰 Financial Reports & Statements")
        
        docs = db.collection('Bookings').stream()
        bookings_list = []
        for doc in docs:
            data = doc.to_dict()
            bookings_list.append({
                'Date': data.get('Date'),
                'Room': data.get('Room'),
                'Name': data.get('Name'),
                'Persons': data.get('Persons', data.get('Beds_Booked', 1)),
                'Total_Bill': data.get('Total_Bill', 0),
                'Advance_Paid': data.get('Advance_Paid', data.get('Advance', 0)),
                'Balance_Pending': data.get('Balance_Pending', data.get('Balance', 0)),
                'Status': data.get('Status', 'Active')
            })
        
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
            st.dataframe(filtered_df[['Date', 'Room', 'Name', 'Persons', 'Status', 'Total_Bill', 'Advance_Paid', 'Balance_Pending']], use_container_width=True)
        else:
            st.info("Abhi tak koi booking nahi hui. Data khali hai.")

    # ==========================================
    # PAGE 4: MANAGE ROOMS
    # ==========================================
    elif menu == "⚙️ Manage Rooms":
        st.title("⚙️ Room Management")
        col1, col2 = st.columns(2)
        
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

        with col2:
            st.subheader("🗑️ Delete a Room")
            with st.form("delete_room_form"):
                room_to_delete = st.selectbox("Select Room to Delete", room_names)
                confirm_delete = st.checkbox(f"Yes, I want to permanently delete {room_to_delete}")
                if st.form_submit_button("Delete Room"):
                    if not confirm_delete:
                        st.warning("Please tick the confirmation box to delete.")
                    else:
                        current_beds = rooms_data[room_to_delete]
                        if True in current_beds:
                            st.error(f"⚠️ App {room_to_delete} ko delete nahi kar sakte kyunke wahan log thehre hue hain!")
                        else:
                            db.collection('Rooms').document(room_to_delete).delete()
                            st.success(f"✅ {room_to_delete} deleted successfully!")
                            st.rerun()
