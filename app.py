import streamlit as st
import pandas as pd
import mysql.connector
from mysql.connector import IntegrityError
from openai import OpenAI
from datetime import datetime, date, time

# ============================================================
# CẤU HÌNH
# ============================================================
st.set_page_config(
    page_title="Destination Flow Manager",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.image("VT2.jpg")



# ============================================================
# DATABASE
# ============================================================

def get_connection():
    return mysql.connector.connect(
        host=st.secrets["mysql"]["host"],
        port=int(st.secrets["mysql"]["port"]),
        user=st.secrets["mysql"]["user"],
        password=st.secrets["mysql"]["password"],
        database=st.secrets["mysql"]["database"],
        ssl_disabled=False,
        connection_timeout=15
    )


def init_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS destinations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) UNIQUE NOT NULL,
            location VARCHAR(255) NOT NULL,
            category VARCHAR(100) NOT NULL,
            capacity INT NOT NULL,
            warning_level INT NOT NULL,
            description TEXT,
            status VARCHAR(50) DEFAULT 'Hoạt động'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS visits (
            id INT AUTO_INCREMENT PRIMARY KEY,
            destination_id INT NOT NULL,
            visitor_name VARCHAR(255),
            visitor_group VARCHAR(100),
            number_of_people INT NOT NULL,
            visit_date DATE NOT NULL,
            visit_time TIME NOT NULL,
            time_slot VARCHAR(100) NOT NULL,
            status VARCHAR(50) DEFAULT 'Đã ghi nhận',
            created_at DATETIME NOT NULL,
            CONSTRAINT fk_visits_destination
                FOREIGN KEY (destination_id)
                REFERENCES destinations(id)
                ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS time_slots (
            id INT AUTO_INCREMENT PRIMARY KEY,
            slot_name VARCHAR(100) NOT NULL,
            start_time VARCHAR(5) NOT NULL,
            end_time VARCHAR(5) NOT NULL,
            max_people INT NOT NULL
        )
    """)

    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM destinations")
    destination_count = cursor.fetchone()[0]

    if destination_count == 0:
        destinations = [
            ("Thích Ca Phật Đài", "Vũng Tàu", "Tâm linh", 1000, 800,
             "Điểm tham quan tâm linh nổi tiếng tại Vũng Tàu", "Hoạt động"),
            ("Bãi Sau Vũng Tàu", "Vũng Tàu", "Biển", 5000, 4000,
             "Khu vực biển có lượng khách cao vào cuối tuần", "Hoạt động"),
            ("Hồ Mây Park", "Vũng Tàu", "Vui chơi", 3000, 2400,
             "Khu vui chơi và du lịch sinh thái", "Hoạt động"),
            ("Khu du lịch Bình Châu", "Xuyên Mộc", "Sinh thái", 2500, 2000,
             "Khu du lịch sinh thái và nghỉ dưỡng", "Hoạt động"),
            ("Long Hải", "Long Điền", "Biển", 3500, 2800,
             "Điểm du lịch biển và nghỉ dưỡng", "Hoạt động"),
            ("Hồ Tràm", "Xuyên Mộc", "Nghỉ dưỡng", 4000, 3200,
             "Khu vực nghỉ dưỡng ven biển", "Hoạt động")
        ]

        cursor.executemany("""
            INSERT INTO destinations
            (name, location, category, capacity, warning_level, description, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, destinations)

    cursor.execute("SELECT COUNT(*) FROM time_slots")
    slot_count = cursor.fetchone()[0]

    if slot_count == 0:
        slots = [
            ("Sáng sớm", "06:00", "09:00", 1000),
            ("Buổi sáng", "09:00", "12:00", 1500),
            ("Buổi trưa", "12:00", "14:00", 1000),
            ("Buổi chiều", "14:00", "17:00", 1500),
            ("Buổi tối", "17:00", "21:00", 2000)
        ]

        cursor.executemany("""
            INSERT INTO time_slots
            (slot_name, start_time, end_time, max_people)
            VALUES (%s, %s, %s, %s)
        """, slots)

    conn.commit()
    cursor.close()
    conn.close()


try:
    init_database()
except Exception as e:
    st.error("❌ Không kết nối được MySQL Aiven.")
    st.exception(e)
    st.stop()


# ============================================================
# DATABASE FUNCTIONS
# ============================================================

def get_destinations():
    conn = get_connection()
    df = pd.read_sql("""
        SELECT *
        FROM destinations
        ORDER BY name
    """, conn)
    conn.close()
    return df


def get_visits():
    conn = get_connection()
    df = pd.read_sql("""
        SELECT
            v.id,
            d.name AS destination,
            d.location,
            d.category,
            v.visitor_name,
            v.visitor_group,
            v.number_of_people,
            DATE_FORMAT(v.visit_date, '%Y-%m-%d') AS visit_date,
            TIME_FORMAT(v.visit_time, '%H:%i') AS visit_time,
            v.time_slot,
            v.status,
            DATE_FORMAT(v.created_at, '%Y-%m-%d %H:%i:%s') AS created_at
        FROM visits v
        JOIN destinations d ON v.destination_id = d.id
        ORDER BY v.id DESC
    """, conn)
    conn.close()
    return df


def get_time_slots():
    conn = get_connection()
    df = pd.read_sql("""
        SELECT *
        FROM time_slots
        ORDER BY start_time
    """, conn)
    conn.close()
    return df


# ============================================================
# XÁC ĐỊNH KHUNG GIỜ
# ============================================================

def get_current_time_slot():
    now = datetime.now().time()
    slots = get_time_slots()

    for _, row in slots.iterrows():
        start = datetime.strptime(str(row["start_time"])[:5], "%H:%M").time()
        end = datetime.strptime(str(row["end_time"])[:5], "%H:%M").time()

        if start <= now <= end:
            return row["slot_name"]

    return "Ngoài khung giờ"


# ============================================================
# TÍNH LƯỢNG KHÁCH
# ============================================================

def get_today_visitors():
    today = date.today().strftime("%Y-%m-%d")
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COALESCE(SUM(number_of_people), 0)
        FROM visits
        WHERE visit_date = %s
          AND status != 'Đã hủy'
    """, (today,))

    result = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return int(result)


def get_destination_visitors(destination_id):
    today = date.today().strftime("%Y-%m-%d")
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COALESCE(SUM(number_of_people), 0)
        FROM visits
        WHERE destination_id = %s
          AND visit_date = %s
          AND status != 'Đã hủy'
    """, (int(destination_id), today))

    result = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return int(result)


def get_slot_visitors(destination_id, slot_name):
    today = date.today().strftime("%Y-%m-%d")
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COALESCE(SUM(number_of_people), 0)
        FROM visits
        WHERE destination_id = %s
          AND time_slot = %s
          AND visit_date = %s
          AND status != 'Đã hủy'
    """, (int(destination_id), slot_name, today))

    result = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return int(result)


# ============================================================
# PHÂN LOẠI MỨC ĐỘ
# ============================================================

def get_load_status(current, warning, capacity):

    if current >= capacity:
        return "🔴 QUÁ TẢI"

    elif current >= warning:
        return "🟠 CAO"

    elif current >= warning * 0.7:
        return "🟡 TRUNG BÌNH"

    else:
        return "🟢 THẤP"


# ============================================================
# GHI NHẬN KHÁCH
# ============================================================

def add_visit(
    destination_id,
    visitor_name,
    visitor_group,
    number_of_people,
    visit_date,
    visit_time,
    time_slot
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO visits
        (
            destination_id,
            visitor_name,
            visitor_group,
            number_of_people,
            visit_date,
            visit_time,
            time_slot,
            status,
            created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        int(destination_id),
        visitor_name,
        visitor_group,
        int(number_of_people),
        visit_date,
        visit_time,
        time_slot,
        "Đã ghi nhận",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    cursor.close()
    conn.close()


# ============================================================
# GIAO DIỆN SIDEBAR
# ============================================================

st.sidebar.title("🌍 DESTINATION")
st.sidebar.title("FLOW MANAGER")

st.sidebar.markdown(
    """
    **Hệ thống quản lý và giảm tải
    lượng khách tại điểm đến**
    """
)

st.sidebar.divider()

menu = st.sidebar.radio(
    "📌 Chức năng",
    [
        "📊 Dashboard",
        "🚦 Giám sát điểm đến",
        "👥 Ghi nhận khách",
        "📅 Phân luồng theo giờ",
        "📍 Quản lý điểm đến",
        "📋 Lịch sử lượt khách",
        "📸 Địa điểm chụp ảnh đẹp Vũng Tàu",
        "🍜 Món ăn địa phương & đặc sản Vũng Tàu",
        "🤖 Chatbot du lịch Vũng Tàu"
    ]
)

st.sidebar.divider()

try:
    test_conn = get_connection()
    if test_conn.is_connected():
        st.sidebar.success("🟢 Đã cấu hình MySQL Aiven")
    test_conn.close()
except Exception:
    st.sidebar.error("🔴 Chưa kết nối MySQL Aiven")

st.sidebar.info(
    "💡 Mục tiêu:\n\n"
    "Theo dõi → Cảnh báo → "
    "Điều phối → Giảm quá tải"
)


# ============================================================
# DASHBOARD
# ============================================================

if menu == "📊 Dashboard":

    st.title("🌍 Destination Flow Manager")

    st.caption(
        "Hệ thống quản lý và điều phối lượng khách tại điểm đến du lịch"
    )

    destinations = get_destinations()

    today_visitors = get_today_visitors()

    total_capacity = destinations["capacity"].sum()

    active_destinations = len(
        destinations[
            destinations["status"] == "Hoạt động"
        ]
    )

    # --------------------------------------------------------
    # KPI
    # --------------------------------------------------------

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric(
        "👥 Khách hôm nay",
        f"{today_visitors:,}"
    )

    col2.metric(
        "📍 Điểm đến",
        active_destinations
    )

    col3.metric(
        "🧍 Sức chứa",
        f"{total_capacity:,}"
    )

    # Công suất tổng
    total_load = (
        today_visitors / total_capacity * 100
        if total_capacity > 0 else 0
    )

    col4.metric(
        "📈 Mức sử dụng",
        f"{total_load:.1f}%"
    )

    overloaded = 0

    for _, row in destinations.iterrows():

        current = get_destination_visitors(
            row["id"]
        )

        if current >= row["capacity"]:
            overloaded += 1

    col5.metric(
        "🔴 Quá tải",
        overloaded
    )

    st.divider()

    # --------------------------------------------------------
    # CẢNH BÁO
    # --------------------------------------------------------

    st.subheader("🚨 Trung tâm cảnh báo")

    warning_found = False

    for _, row in destinations.iterrows():

        current = get_destination_visitors(
            row["id"]
        )

        status = get_load_status(
            current,
            row["warning_level"],
            row["capacity"]
        )

        if "QUÁ TẢI" in status:

            warning_found = True

            st.error(
                f"🔴 **{row['name']}** đang QUÁ TẢI: "
                f"{current:,}/{row['capacity']:,} khách."
            )

        elif "CAO" in status:

            warning_found = True

            st.warning(
                f"🟠 **{row['name']}** đang có lượng khách cao: "
                f"{current:,}/{row['capacity']:,}."
            )

    if not warning_found:

        st.success(
            "🟢 Chưa phát hiện điểm đến có nguy cơ quá tải."
        )

    st.divider()

    # --------------------------------------------------------
    # BẢNG ĐIỂM ĐẾN
    # --------------------------------------------------------

    st.subheader("📍 Tình trạng các điểm đến")

    dashboard_data = []

    for _, row in destinations.iterrows():

        current = get_destination_visitors(
            row["id"]
        )

        percentage = (
            current / row["capacity"] * 100
            if row["capacity"] > 0 else 0
        )

        status = get_load_status(
            current,
            row["warning_level"],
            row["capacity"]
        )

        dashboard_data.append({

            "Điểm đến": row["name"],

            "Khu vực": row["location"],

            "Loại hình": row["category"],

            "Khách hiện tại": current,

            "Sức chứa": row["capacity"],

            "Mức sử dụng": f"{percentage:.1f}%",

            "Trạng thái": status

        })

    dashboard_df = pd.DataFrame(
        dashboard_data
    )

    st.dataframe(
        dashboard_df,
        use_container_width=True,
        hide_index=True
    )

    # --------------------------------------------------------
    # BIỂU ĐỒ
    # --------------------------------------------------------

    st.subheader("📊 Lượng khách theo điểm đến")

    chart_df = dashboard_df[
        ["Điểm đến", "Khách hiện tại"]
    ].set_index("Điểm đến")

    st.bar_chart(chart_df)

    # --------------------------------------------------------
    # GỢI Ý PHÂN LUỒNG
    # --------------------------------------------------------

    st.subheader("🧭 Gợi ý điều phối")

    high_destinations = []

    low_destinations = []

    for _, row in destinations.iterrows():

        current = get_destination_visitors(
            row["id"]
        )

        percentage = (
            current / row["capacity"]
        )

        if percentage >= 0.8:

            high_destinations.append(
                row["name"]
            )

        elif percentage < 0.5:

            low_destinations.append(
                row["name"]
            )

    if high_destinations:

        st.warning(
            "⚠️ Nên hạn chế tiếp nhận thêm khách "
            f"tại: **{', '.join(high_destinations)}**"
        )

    if low_destinations:

        st.info(
            "🟢 Có thể điều hướng khách sang "
            f"các điểm đang ít khách: **{', '.join(low_destinations)}**"
        )


# ============================================================
# GIÁM SÁT ĐIỂM ĐẾN
# ============================================================

elif menu == "🚦 Giám sát điểm đến":

    st.title("🚦 Giám sát sức chứa điểm đến")

    destinations = get_destinations()

    selected = st.selectbox(
        "Chọn điểm đến",
        destinations["name"].tolist()
    )

    destination = destinations[
        destinations["name"] == selected
    ].iloc[0]

    current = get_destination_visitors(
        destination["id"]
    )

    percentage = (
        current / destination["capacity"] * 100
        if destination["capacity"] > 0 else 0
    )

    status = get_load_status(
        current,
        destination["warning_level"],
        destination["capacity"]
    )

    # --------------------------------------------------------
    # THÔNG TIN
    # --------------------------------------------------------

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "👥 Khách hôm nay",
        f"{current:,}"
    )

    col2.metric(
        "🏟️ Sức chứa",
        f"{destination['capacity']:,}"
    )

    col3.metric(
        "📈 Mức sử dụng",
        f"{percentage:.1f}%"
    )

    col4.metric(
        "🚦 Trạng thái",
        status
    )

    st.divider()

    # --------------------------------------------------------
    # THANH SỨC CHỨA
    # --------------------------------------------------------

    st.subheader("📊 Mức sử dụng sức chứa")

    progress = min(
        percentage / 100,
        1
    )

    st.progress(progress)

    if percentage >= 100:

        st.error(
            "🔴 ĐIỂM ĐẾN ĐANG QUÁ TẢI"
        )

        st.warning(
            "Nên tạm thời hạn chế khách mới "
            "và chuyển một phần khách sang điểm thay thế."
        )

    elif percentage >= 80:

        st.warning(
            "🟠 Lượng khách đang cao. "
            "Nên kiểm soát lượt khách mới."
        )

    elif percentage >= 50:

        st.info(
            "🟡 Lượng khách ở mức trung bình."
        )

    else:

        st.success(
            "🟢 Điểm đến còn nhiều khả năng tiếp nhận khách."
        )

    st.divider()

    # --------------------------------------------------------
    # KHUNG GIỜ
    # --------------------------------------------------------

    st.subheader("⏰ Phân bố khách theo khung giờ")

    slots = get_time_slots()

    slot_data = []

    for _, slot in slots.iterrows():

        visitors = get_slot_visitors(
            destination["id"],
            slot["slot_name"]
        )

        slot_data.append({

            "Khung giờ":
                slot["slot_name"],

            "Thời gian":
                f"{slot['start_time']} - "
                f"{slot['end_time']}",

            "Số khách":
                visitors,

            "Giới hạn":
                slot["max_people"]

        })

    slot_df = pd.DataFrame(
        slot_data
    )

    st.dataframe(
        slot_df,
        use_container_width=True,
        hide_index=True
    )

    st.bar_chart(
        slot_df.set_index("Khung giờ")[
            ["Số khách"]
        ]
    )


# ============================================================
# GHI NHẬN KHÁCH
# ============================================================

elif menu == "👥 Ghi nhận khách":

    st.title("👥 Ghi nhận lượt khách")

    st.info(
        "Nhập thông tin đoàn khách để hệ thống "
        "tự động cập nhật lượng khách tại điểm đến."
    )

    destinations = get_destinations()

    with st.form("visitor_form"):

        destination_name = st.selectbox(
            "📍 Điểm đến",
            destinations["name"].tolist()
        )

        destination = destinations[
            destinations["name"] == destination_name
        ].iloc[0]

        col1, col2 = st.columns(2)

        with col1:

            visitor_name = st.text_input(
                "Tên người đại diện / trưởng đoàn",
                placeholder="Ví dụ: Nguyễn Văn A"
            )

            visitor_group = st.selectbox(
                "👥 Loại khách",
                [
                    "Khách lẻ",
                    "Gia đình",
                    "Đoàn du lịch",
                    "Học sinh - sinh viên",
                    "Doanh nghiệp",
                    "Khách quốc tế"
                ]
            )

        with col2:

            number_of_people = st.number_input(
                "Số lượng người",
                min_value=1,
                max_value=10000,
                value=1
            )

            visit_date = st.date_input(
                "Ngày đến",
                value=date.today()
            )

            visit_time = st.time_input(
                "Thời gian đến",
                value=datetime.now().time()
            )

        slots = get_time_slots()

        slot_names = slots[
            "slot_name"
        ].tolist()

        time_slot = st.selectbox(
            "⏰ Khung giờ dự kiến",
            slot_names
        )

        submitted = st.form_submit_button(
            "✅ Ghi nhận lượt khách",
            type="primary"
        )

        if submitted:

            current = get_destination_visitors(
                destination["id"]
            )

            new_total = (
                current + number_of_people
            )

            if new_total >= destination["capacity"]:

                st.error(
                    f"🔴 Cảnh báo: nếu ghi nhận đoàn này, "
                    f"điểm đến sẽ đạt {new_total:,}/"
                    f"{destination['capacity']:,} khách."
                )

                confirm = st.checkbox(
                    "Tôi xác nhận vẫn muốn ghi nhận lượt khách này."
                )

                if confirm:

                    add_visit(
                        destination["id"],
                        visitor_name,
                        visitor_group,
                        number_of_people,
                        visit_date.strftime("%Y-%m-%d"),
                        visit_time.strftime("%H:%M"),
                        time_slot
                    )

                    st.success(
                        "Đã ghi nhận lượt khách."
                    )

            else:

                add_visit(
                    destination["id"],
                    visitor_name,
                    visitor_group,
                    number_of_people,
                    visit_date.strftime("%Y-%m-%d"),
                    visit_time.strftime("%H:%M"),
                    time_slot
                )

                st.success(
                    "✅ Đã ghi nhận lượt khách thành công."
                )

                remaining = (
                    destination["capacity"]
                    - new_total
                )

                st.info(
                    f"Điểm đến còn khoảng "
                    f"**{remaining:,} lượt** "
                    "theo sức chứa thiết lập."
                )

                st.rerun()


# ============================================================
# PHÂN LUỒNG THEO GIỜ
# ============================================================

elif menu == "📅 Phân luồng theo giờ":

    st.title("📅 Điều phối khách theo khung giờ")

    st.write(
        "Mục tiêu là phân tán lượng khách, "
        "tránh việc quá nhiều người tập trung "
        "vào cùng một thời điểm."
    )

    destinations = get_destinations()
    slots = get_time_slots()

    selected_destination = st.selectbox(
        "📍 Chọn điểm đến",
        destinations["name"].tolist()
    )

    destination = destinations[
        destinations["name"] == selected_destination
    ].iloc[0]

    st.divider()

    data = []

    for _, slot in slots.iterrows():

        visitors = get_slot_visitors(
            destination["id"],
            slot["slot_name"]
        )

        capacity = slot["max_people"]

        percentage = (
            visitors / capacity * 100
            if capacity > 0 else 0
        )

        if percentage >= 100:

            status = "🔴 Đầy"

        elif percentage >= 80:

            status = "🟠 Gần đầy"

        elif percentage >= 50:

            status = "🟡 Trung bình"

        else:

            status = "🟢 Còn nhiều chỗ"

        data.append({

            "Khung giờ":
                slot["slot_name"],

            "Thời gian":
                f"{slot['start_time']} - "
                f"{slot['end_time']}",

            "Khách":
                visitors,

            "Giới hạn":
                capacity,

            "Sử dụng":
                f"{percentage:.1f}%",

            "Trạng thái":
                status

        })

    slot_df = pd.DataFrame(data)

    st.dataframe(
        slot_df,
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    st.subheader(
        "🧭 Khuyến nghị điều phối"
    )

    for _, row in slot_df.iterrows():

        if "Đầy" in row["Trạng thái"]:

            st.error(
                f"🔴 **{row['Khung giờ']}** đang đầy. "
                "Nên hạn chế khách mới trong khung giờ này."
            )

        elif "Gần đầy" in row["Trạng thái"]:

            st.warning(
                f"🟠 **{row['Khung giờ']}** gần đạt giới hạn. "
                "Có thể hướng khách sang khung giờ khác."
            )

        elif "Còn nhiều" in row["Trạng thái"]:

            st.success(
                f"🟢 **{row['Khung giờ']}** còn khả năng "
                "tiếp nhận thêm khách."
            )

    st.divider()

    st.subheader(
        "💡 Nguyên tắc phân luồng"
    )

    st.markdown(
        """
        **Nếu một khung giờ quá đông:**

        🔴 Giảm tiếp nhận khách mới  
        ↓  
        🟠 Đề xuất khung giờ ít khách hơn  
        ↓  
        🟢 Nếu vẫn đông, đề xuất điểm đến thay thế  
        ↓  
        📊 Theo dõi lại lượng khách
        """
    )


# ============================================================
# QUẢN LÝ ĐIỂM ĐẾN
# ============================================================

elif menu == "📍 Quản lý điểm đến":

    st.title("📍 Quản lý điểm đến")

    destinations = get_destinations()

    st.subheader("Danh sách điểm đến")

    display_df = destinations[
        [
            "name",
            "location",
            "category",
            "capacity",
            "warning_level",
            "status"
        ]
    ].copy()

    display_df.columns = [
        "Điểm đến",
        "Khu vực",
        "Loại hình",
        "Sức chứa",
        "Ngưỡng cảnh báo",
        "Trạng thái"
    ]

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    st.subheader("➕ Thêm điểm đến")

    with st.form("destination_form"):

        name = st.text_input(
            "Tên điểm đến"
        )

        location = st.text_input(
            "Khu vực"
        )

        category = st.selectbox(
            "Loại hình",
            [
                "Biển",
                "Sinh thái",
                "Tâm linh",
                "Vui chơi",
                "Nghỉ dưỡng",
                "Văn hóa",
                "Lịch sử",
                "Khác"
            ]
        )

        col1, col2 = st.columns(2)

        with col1:

            capacity = st.number_input(
                "Sức chứa tối đa",
                min_value=1,
                value=1000
            )

        with col2:

            warning_level = st.number_input(
                "Ngưỡng cảnh báo",
                min_value=1,
                value=800
            )

        description = st.text_area(
            "Mô tả"
        )

        submitted = st.form_submit_button(
            "➕ Thêm điểm đến",
            type="primary"
        )

        if submitted:

            if not name.strip():

                st.error(
                    "Vui lòng nhập tên điểm đến."
                )

            elif not location.strip():

                st.error(
                    "Vui lòng nhập khu vực."
                )

            elif warning_level > capacity:

                st.error(
                    "Ngưỡng cảnh báo không được "
                    "lớn hơn sức chứa."
                )

            else:

                try:

                    conn = get_connection()
                    cursor = conn.cursor()

                    cursor.execute("""
                        INSERT INTO destinations
                        (
                            name,
                            location,
                            category,
                            capacity,
                            warning_level,
                            description,
                            status
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        name.strip(),
                        location.strip(),
                        category,
                        int(capacity),
                        int(warning_level),
                        description,
                        "Hoạt động"
                    ))

                    conn.commit()
                    cursor.close()
                    conn.close()

                    st.success(
                        f"Đã thêm điểm đến: {name}"
                    )

                    st.rerun()

                except IntegrityError:

                    st.error(
                        "Điểm đến này đã tồn tại."
                    )


# ============================================================
# LỊCH SỬ
# ============================================================

elif menu == "📋 Lịch sử lượt khách":

    st.title("📋 Lịch sử lượt khách")

    visits = get_visits()

    if len(visits) == 0:

        st.info(
            "Chưa có dữ liệu lượt khách."
        )

    else:

        # ----------------------------------------------------
        # BỘ LỌC
        # ----------------------------------------------------

        col1, col2, col3 = st.columns(3)

        with col1:

            destination_filter = st.selectbox(
                "📍 Điểm đến",
                ["Tất cả"]
                + sorted(
                    visits["destination"]
                    .dropna()
                    .unique()
                    .tolist()
                )
            )

        with col2:

            group_filter = st.selectbox(
                "👥 Nhóm khách",
                ["Tất cả"]
                + sorted(
                    visits["visitor_group"]
                    .dropna()
                    .unique()
                    .tolist()
                )
            )

        with col3:

            date_filter = st.date_input(
                "📅 Ngày",
                value=date.today()
            )

        filtered = visits.copy()

        if destination_filter != "Tất cả":

            filtered = filtered[
                filtered["destination"]
                == destination_filter
            ]

        if group_filter != "Tất cả":

            filtered = filtered[
                filtered["visitor_group"]
                == group_filter
            ]

        filtered = filtered[
            filtered["visit_date"]
            == date_filter.strftime("%Y-%m-%d")
        ]

        # ----------------------------------------------------
        # KPI
        # ----------------------------------------------------

        total_people = filtered[
            "number_of_people"
        ].sum()

        total_groups = len(filtered)

        c1, c2 = st.columns(2)

        c1.metric(
            "👥 Tổng lượt khách",
            f"{int(total_people):,}"
        )

        c2.metric(
            "🎫 Số lượt ghi nhận",
            total_groups
        )

        st.divider()

        st.dataframe(
            filtered[
                [
                    "destination",
                    "visitor_name",
                    "visitor_group",
                    "number_of_people",
                    "visit_date",
                    "visit_time",
                    "time_slot",
                    "status"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

        # ----------------------------------------------------
        # DOWNLOAD
        # ----------------------------------------------------

        csv = filtered.to_csv(
            index=False
        ).encode("utf-8-sig")

        st.download_button(
            "⬇️ Xuất dữ liệu CSV",
            data=csv,
            file_name=(
                f"visitor_data_"
                f"{date_filter.strftime('%Y%m%d')}.csv"
            ),
            mime="text/csv"
        )



# ============================================================
# ĐỊA ĐIỂM CHỤP ẢNH ĐẸP VŨNG TÀU
# ============================================================

elif menu == "📸 Địa điểm chụp ảnh đẹp Vũng Tàu":

    st.title("📸 Địa điểm chụp ảnh đẹp Vũng Tàu")

    st.caption(
        "Gợi ý các địa điểm check-in theo phong cách, thời gian "
        "và khu vực bạn mong muốn."
    )

    photo_places = pd.DataFrame([
        {
            "Tên địa điểm": "Mũi Nghinh Phong",
            "Khu vực": "Phường 2",
            "Phong cách": "Biển - thiên nhiên",
            "Thời gian đẹp": "Chiều",
            "Điểm nổi bật": "Biển, vách đá, không gian thoáng"
        },
        {
            "Tên địa điểm": "Đồi Con Heo",
            "Khu vực": "Phường 2",
            "Phong cách": "Đồi - toàn cảnh",
            "Thời gian đẹp": "Chiều",
            "Điểm nổi bật": "View cao, nhìn thành phố và biển"
        },
        {
            "Tên địa điểm": "Hải đăng Vũng Tàu",
            "Khu vực": "Núi Nhỏ",
            "Phong cách": "Cổ điển - toàn cảnh",
            "Thời gian đẹp": "Sáng",
            "Điểm nổi bật": "Hải đăng trắng, đường núi, view thành phố"
        },
        {
            "Tên địa điểm": "Tượng Chúa Kitô Vua",
            "Khu vực": "Núi Nhỏ",
            "Phong cách": "Kiến trúc - toàn cảnh",
            "Thời gian đẹp": "Sáng",
            "Điểm nổi bật": "Kiến trúc nổi bật, góc nhìn từ trên cao"
        },
        {
            "Tên địa điểm": "Hẻm Trần Phú",
            "Khu vực": "Trần Phú",
            "Phong cách": "Đường phố - biển",
            "Thời gian đẹp": "Chiều",
            "Điểm nổi bật": "Hẻm nhỏ hướng ra biển, phong cách nhẹ nhàng"
        },
        {
            "Tên địa điểm": "Bãi Dâu",
            "Khu vực": "Trần Phú",
            "Phong cách": "Biển - yên tĩnh",
            "Thời gian đẹp": "Chiều",
            "Điểm nổi bật": "Không gian biển yên tĩnh, ít đông hơn"
        }
    ])

    with st.form("photo_place_filter_form"):

        st.subheader("🔎 Tìm địa điểm phù hợp")

        c1, c2, c3 = st.columns(3)

        with c1:
            photo_style = st.selectbox(
                "Phong cách chụp ảnh",
                [
                    "Tất cả",
                    "Biển - thiên nhiên",
                    "Đồi - toàn cảnh",
                    "Cổ điển - toàn cảnh",
                    "Kiến trúc - toàn cảnh",
                    "Đường phố - biển",
                    "Biển - yên tĩnh"
                ]
            )

        with c2:
            photo_time = st.selectbox(
                "Thời gian muốn đi",
                ["Tất cả", "Sáng", "Chiều"]
            )

        with c3:
            photo_area = st.selectbox(
                "Khu vực",
                ["Tất cả"] + sorted(photo_places["Khu vực"].unique().tolist())
            )

        find_photo = st.form_submit_button(
            "📸 Tìm địa điểm",
            type="primary"
        )

    filtered_photo = photo_places.copy()

    if photo_style != "Tất cả":
        filtered_photo = filtered_photo[
            filtered_photo["Phong cách"] == photo_style
        ]

    if photo_time != "Tất cả":
        filtered_photo = filtered_photo[
            filtered_photo["Thời gian đẹp"] == photo_time
        ]

    if photo_area != "Tất cả":
        filtered_photo = filtered_photo[
            filtered_photo["Khu vực"] == photo_area
        ]

    if find_photo:
        if len(filtered_photo) == 0:
            st.warning("Không tìm thấy địa điểm phù hợp với lựa chọn.")
        else:
            st.success(
                f"Tìm thấy {len(filtered_photo)} địa điểm phù hợp."
            )

    st.subheader("📍 Danh sách gợi ý")

    st.dataframe(
        filtered_photo,
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    st.subheader("💡 Gợi ý nhanh")

    if len(filtered_photo) > 0:
        for _, place in filtered_photo.iterrows():
            with st.expander(f"📸 {place['Tên địa điểm']}"):
                st.write(f"**Khu vực:** {place['Khu vực']}")
                st.write(f"**Phong cách:** {place['Phong cách']}")
                st.write(f"**Thời gian đẹp:** {place['Thời gian đẹp']}")
                st.write(f"**Điểm nổi bật:** {place['Điểm nổi bật']}")


# ============================================================
# MÓN ĂN ĐỊA PHƯƠNG & ĐẶC SẢN VŨNG TÀU
# ============================================================

elif menu == "🍜 Món ăn địa phương & đặc sản Vũng Tàu":

    st.title("🍜 Món ăn địa phương & đặc sản Vũng Tàu")

    st.caption(
        "Tìm món ăn phù hợp theo loại món, mức giá "
        "và thời điểm thưởng thức."
    )

    local_foods = pd.DataFrame([
        {
            "Món ăn": "Bánh khọt Vũng Tàu",
            "Loại món": "Ăn chính",
            "Mức giá": "Bình dân",
            "Thời điểm": "Sáng",
            "Mô tả": "Bánh nhỏ giòn, thường ăn cùng rau sống và nước mắm"
        },
        {
            "Món ăn": "Lẩu cá đuối",
            "Loại món": "Ăn chính",
            "Mức giá": "Trung bình",
            "Thời điểm": "Tối",
            "Mô tả": "Món lẩu chua cay, thường dùng cho nhóm bạn hoặc gia đình"
        },
        {
            "Món ăn": "Hải sản Vũng Tàu",
            "Loại món": "Hải sản",
            "Mức giá": "Trung bình",
            "Thời điểm": "Tối",
            "Mô tả": "Nhiều lựa chọn như tôm, cua, ghẹ, mực và các loại ốc"
        },
        {
            "Món ăn": "Bông lan trứng muối",
            "Loại món": "Ăn vặt",
            "Mức giá": "Bình dân",
            "Thời điểm": "Chiều",
            "Mô tả": "Bánh mềm, vị mặn ngọt, phù hợp mua làm quà"
        },
        {
            "Món ăn": "Gỏi cá mai",
            "Loại món": "Hải sản",
            "Mức giá": "Trung bình",
            "Thời điểm": "Trưa",
            "Mô tả": "Món gỏi cá ăn kèm rau và nước chấm"
        },
        {
            "Món ăn": "Bánh tiêu đậu xanh",
            "Loại món": "Ăn vặt",
            "Mức giá": "Bình dân",
            "Thời điểm": "Chiều",
            "Mô tả": "Bánh tiêu thơm, nhân đậu xanh, thích hợp ăn nhẹ"
        }
    ])

    with st.form("local_food_filter_form"):

        st.subheader("🔎 Chọn món phù hợp")

        c1, c2, c3 = st.columns(3)

        with c1:
            food_type = st.selectbox(
                "Loại món",
                [
                    "Tất cả",
                    "Ăn chính",
                    "Hải sản",
                    "Ăn vặt"
                ]
            )

        with c2:
            food_price = st.selectbox(
                "Mức giá",
                ["Tất cả", "Bình dân", "Trung bình"]
            )

        with c3:
            food_time = st.selectbox(
                "Thời điểm",
                ["Tất cả", "Sáng", "Trưa", "Chiều", "Tối"]
            )

        find_food = st.form_submit_button(
            "🍽️ Tìm món ăn",
            type="primary"
        )

    filtered_food = local_foods.copy()

    if food_type != "Tất cả":
        filtered_food = filtered_food[
            filtered_food["Loại món"] == food_type
        ]

    if food_price != "Tất cả":
        filtered_food = filtered_food[
            filtered_food["Mức giá"] == food_price
        ]

    if food_time != "Tất cả":
        filtered_food = filtered_food[
            filtered_food["Thời điểm"] == food_time
        ]

    if find_food:
        if len(filtered_food) == 0:
            st.warning("Không tìm thấy món ăn phù hợp với lựa chọn.")
        else:
            st.success(
                f"Tìm thấy {len(filtered_food)} món phù hợp."
            )

    st.subheader("🍴 Danh sách món ăn")

    st.dataframe(
        filtered_food,
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    st.subheader("⭐ Thông tin món")

    if len(filtered_food) > 0:
        for _, food in filtered_food.iterrows():
            with st.expander(f"🍜 {food['Món ăn']}"):
                st.write(f"**Loại món:** {food['Loại món']}")
                st.write(f"**Mức giá:** {food['Mức giá']}")
                st.write(f"**Thời điểm:** {food['Thời điểm']}")
                st.write(f"**Mô tả:** {food['Mô tả']}")



# ============================================================
# CHATBOT DU LỊCH VŨNG TÀU
# ============================================================

elif menu == "🤖 Chatbot du lịch Vũng Tàu":

    st.title("🤖 Chatbot du lịch Vũng Tàu")

    st.caption(
        "Hỏi AI về địa điểm tham quan, món ăn, chụp ảnh, "
        "lịch trình và kinh nghiệm du lịch Vũng Tàu."
    )

    if "OPENAI_API_KEY" not in st.secrets:
        st.error(
            "Chưa tìm thấy OPENAI_API_KEY trong Streamlit Secrets."
        )
        st.stop()

    client = OpenAI(
        api_key=st.secrets["OPENAI_API_KEY"]
    )

    if "vt_chat_messages" not in st.session_state:
        st.session_state.vt_chat_messages = [
            {
                "role": "assistant",
                "content": (
                    "Xin chào 👋 Tôi là trợ lý du lịch Vũng Tàu. "
                    "Bạn muốn hỏi về địa điểm, món ăn hay lịch trình?"
                )
            }
        ]

    col_clear, _ = st.columns([1, 5])

    with col_clear:
        if st.button("🗑️ Xóa hội thoại"):
            st.session_state.vt_chat_messages = [
                {
                    "role": "assistant",
                    "content": (
                        "Xin chào 👋 Tôi là trợ lý du lịch Vũng Tàu. "
                        "Bạn muốn hỏi về địa điểm, món ăn hay lịch trình?"
                    )
                }
            ]
            st.rerun()

    for message in st.session_state.vt_chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input(
        "Ví dụ: Đi Vũng Tàu 2 ngày 1 đêm nên đi đâu?"
    )

    if prompt:

        st.session_state.vt_chat_messages.append(
            {
                "role": "user",
                "content": prompt
            }
        )

        with st.chat_message("user"):
            st.markdown(prompt)

        # Gửi một phần lịch sử hội thoại để AI hiểu ngữ cảnh.
        recent_messages = st.session_state.vt_chat_messages[-10:]

        conversation_text = "\n".join(
            [
                (
                    "Người dùng: " + m["content"]
                    if m["role"] == "user"
                    else "Trợ lý: " + m["content"]
                )
                for m in recent_messages
            ]
        )

        with st.chat_message("assistant"):

            try:
                with st.spinner("Đang trả lời..."):

                    response = client.responses.create(
                        model="gpt-5.6-luna",
                        instructions="""
Bạn là trợ lý du lịch Vũng Tàu trong ứng dụng Destination Flow Manager.

Yêu cầu:
- Trả lời bằng tiếng Việt, dễ hiểu và thân thiện.
- Tập trung vào Vũng Tàu và khu vực lân cận.
- Có thể tư vấn địa điểm tham quan, địa điểm chụp ảnh,
  món ăn, đặc sản, lịch trình, thời gian đi và gợi ý hoạt động.
- Nếu người dùng hỏi giá, giờ mở cửa, địa chỉ hoặc thông tin
  có thể thay đổi theo thời gian mà bạn không chắc chắn,
  hãy nói rõ rằng họ nên kiểm tra lại trước khi đi.
- Không bịa thông tin.
- Trả lời ngắn gọn, ưu tiên gợi ý thực tế.
""",
                        input=conversation_text
                    )

                    answer = response.output_text.strip()

                    if not answer:
                        answer = (
                            "Mình chưa tạo được câu trả lời. "
                            "Bạn thử hỏi lại theo cách khác nhé."
                        )

                    st.markdown(answer)

                    st.session_state.vt_chat_messages.append(
                        {
                            "role": "assistant",
                            "content": answer
                        }
                    )

           import streamlit as st
from openai import OpenAI

# =========================
# OPENAI CLIENT
# =========================
try:
    api_key = st.secrets["OPENAI_API_KEY"]

    if not api_key:
        st.error("Chưa nhập OPENAI_API_KEY trong Streamlit Secrets.")
        st.stop()

    client = OpenAI(api_key=api_key)

except Exception as e:
    st.error(f"Lỗi cấu hình OpenAI: {e}")
    st.stop()


# =========================
# CHATBOT
# =========================

st.subheader("🤖 Trợ lý du lịch Vũng Tàu")

# Lưu lịch sử chat
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Xin chào! 👋 Tôi là trợ lý du lịch Vũng Tàu. "
                "Bạn có thể hỏi tôi về địa điểm du lịch, món ăn, "
                "đặc sản, lịch trình hoặc các tour tại Vũng Tàu."
            )
        }
    ]


# Hiển thị lịch sử
for message in st.session_state.messages:

    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# Ô nhập câu hỏi
prompt = st.chat_input(
    "Bạn muốn hỏi gì về Vũng Tàu?"
)


if prompt:

    # Hiển thị câu hỏi của khách
    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt
        }
    )

    with st.chat_message("user"):
        st.markdown(prompt)


    # =========================
    # GỌI OPENAI
    # =========================

    with st.chat_message("assistant"):

        try:

            # Chỉ gửi lịch sử cần thiết
            history = []

            for message in st.session_state.messages:

                history.append(
                    {
                        "role": message["role"],
                        "content": message["content"]
                    }
                )


            response = client.responses.create(

                # Model
                model="gpt-5.5",

                # Hướng dẫn chatbot
                instructions="""
Bạn là trợ lý du lịch chuyên về Vũng Tàu.

Hãy trả lời bằng tiếng Việt, thân thiện, dễ hiểu
và ngắn gọn.

Bạn có thể hỗ trợ khách:
- Địa điểm du lịch Vũng Tàu
- Địa điểm chụp ảnh đẹp
- Món ăn ngon
- Đặc sản Vũng Tàu
- Gợi ý lịch trình
- Tour du lịch
- Kinh nghiệm tham quan
- Gợi ý địa điểm phù hợp với gia đình, nhóm bạn
- Tư vấn thời gian tham quan

Nếu không chắc chắn về thông tin, hãy nói rõ
thay vì tự bịa thông tin.

Ưu tiên đưa ra câu trả lời thực tế cho khách du lịch.
""",

                # Lịch sử hội thoại
                input=history,

                # Giới hạn câu trả lời
                max_output_tokens=800
            )


            # Lấy nội dung trả lời
            answer = response.output_text


            # Kiểm tra câu trả lời
            if not answer:

                answer = (
                    "Xin lỗi, hiện tại tôi chưa nhận được "
                    "câu trả lời từ hệ thống."
                )


            # Hiển thị
            st.markdown(answer)


            # Lưu vào lịch sử
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": answer
                }
            )


        # =========================
        # XỬ LÝ LỖI
        # =========================

        except Exception as e:

            error_text = str(e)

            if "insufficient_quota" in error_text.lower():

                st.error(
                    "⚠️ Tài khoản OpenAI hiện không còn quota/credits."
                )

                st.info(
                    "Hãy kiểm tra Billing và API usage "
                    "trên OpenAI Platform."
                )


            elif (
                "invalid api key" in error_text.lower()
                or "authentication" in error_text.lower()
            ):

                st.error(
                    "❌ OPENAI_API_KEY không hợp lệ."
                )

                st.info(
                    "Hãy kiểm tra lại OPENAI_API_KEY "
                    "trong Streamlit Secrets."
                )


            elif "model" in error_text.lower():

                st.error(
                    "❌ Model OpenAI không khả dụng."
                )

                st.code(error_text)


            else:

                st.error(
                    "❌ Không gọi được OpenAI API."
                )

                st.code(error_text)


# ============================================================
# FOOTER
# ============================================================

st.sidebar.divider()

st.sidebar.caption(
    "🌍 Destination Flow Manager"
)

st.sidebar.caption(
    "Quản lý • Giám sát • Cảnh báo • Phân luồng"
)
