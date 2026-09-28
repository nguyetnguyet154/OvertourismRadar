import streamlit as st
import pandas as pd
import mysql.connector
from mysql.connector import IntegrityError
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
        "📋 Lịch sử lượt khách"
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
# FOOTER
# ============================================================

st.sidebar.divider()

st.sidebar.caption(
    "🌍 Destination Flow Manager"
)

st.sidebar.caption(
    "Quản lý • Giám sát • Cảnh báo • Phân luồng"
)
