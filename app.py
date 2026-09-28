import streamlit as st
import pymysql
import pandas as pd

from datetime import datetime, date, time
from pymysql.cursors import DictCursor

st.image("VT2.jpg")
# ============================================================
# 1. CẤU HÌNH STREAMLIT
# ============================================================

st.set_page_config(
    page_title="Destination Flow Manager",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# 2. THÔNG TIN KẾT NỐI AIVEN MYSQL
# ============================================================

DB_HOST = "mysql-29a6db25-tranthikimnguyet8-df0c.i.aivencloud.com"
DB_PORT = 19586
DB_USER = "avnadmin"
DB_PASSWORD = "AVNS_6y8qIYGcoOj22F0rJKB"
DB_NAME = "defaultdb"


# ============================================================
# 3. KẾT NỐI DATABASE
# ============================================================

@st.cache_resource(show_spinner=False)
def get_connection():

    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,

        charset="utf8mb4",

        cursorclass=DictCursor,

        connect_timeout=15,
        read_timeout=30,
        write_timeout=30,

        autocommit=False
    )


def reconnect():

    try:
        get_connection.clear()
    except Exception:
        pass

    return get_connection()


# ============================================================
# 4. CHẠY SQL
# ============================================================

def execute_query(
    query,
    params=None,
    fetch=False,
    many=False
):

    connection = None

    try:

        connection = get_connection()

        with connection.cursor() as cursor:

            if many:
                cursor.executemany(
                    query,
                    params
                )

            else:
                cursor.execute(
                    query,
                    params
                )

            if fetch:
                result = cursor.fetchall()

            else:
                result = cursor.lastrowid

        connection.commit()

        return result

    except pymysql.MySQLError as e:

        if connection:
            connection.rollback()

        # Thử kết nối lại một lần
        try:

            connection = reconnect()

            with connection.cursor() as cursor:

                if many:
                    cursor.executemany(
                        query,
                        params
                    )

                else:
                    cursor.execute(
                        query,
                        params
                    )

                if fetch:
                    result = cursor.fetchall()

                else:
                    result = cursor.lastrowid

            connection.commit()

            return result

        except Exception as retry_error:

            if connection:
                connection.rollback()

            st.error(
                f"❌ Lỗi MySQL: {retry_error}"
            )

            return None

    except Exception as e:

        if connection:
            connection.rollback()

        st.error(
            f"❌ Lỗi hệ thống: {e}"
        )

        return None


# ============================================================
# 5. KHỞI TẠO DATABASE
# ============================================================

def initialize_database():

    connection = None

    try:

        connection = get_connection()

        with connection.cursor() as cursor:

            # ------------------------------------------------
            # BẢNG ĐIỂM ĐẾN
            # ------------------------------------------------

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS destinations (

                    id INT AUTO_INCREMENT PRIMARY KEY,

                    name VARCHAR(255) NOT NULL UNIQUE,

                    location VARCHAR(255) NOT NULL,

                    category VARCHAR(100) NOT NULL,

                    capacity INT NOT NULL,

                    warning_level INT NOT NULL,

                    description TEXT,

                    status VARCHAR(50)
                    DEFAULT 'Hoạt động',

                    created_at DATETIME
                    DEFAULT CURRENT_TIMESTAMP,

                    INDEX idx_destination_status (status)

                ) ENGINE=InnoDB
                DEFAULT CHARSET=utf8mb4
                COLLATE=utf8mb4_unicode_ci
            """)

            # ------------------------------------------------
            # BẢNG KHUNG GIỜ
            # ------------------------------------------------

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS time_slots (

                    id INT AUTO_INCREMENT PRIMARY KEY,

                    slot_name VARCHAR(100) NOT NULL,

                    start_time TIME NOT NULL,

                    end_time TIME NOT NULL,

                    max_people INT NOT NULL

                ) ENGINE=InnoDB
                DEFAULT CHARSET=utf8mb4
                COLLATE=utf8mb4_unicode_ci
            """)

            # ------------------------------------------------
            # BẢNG LƯỢT KHÁCH
            # ------------------------------------------------

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

                    status VARCHAR(50)
                    DEFAULT 'Đã ghi nhận',

                    created_at DATETIME
                    DEFAULT CURRENT_TIMESTAMP,

                    CONSTRAINT fk_visit_destination

                    FOREIGN KEY (destination_id)

                    REFERENCES destinations(id)

                    ON DELETE CASCADE,

                    INDEX idx_visit_date (visit_date),

                    INDEX idx_visit_destination (destination_id),

                    INDEX idx_visit_slot (time_slot)

                ) ENGINE=InnoDB
                DEFAULT CHARSET=utf8mb4
                COLLATE=utf8mb4_unicode_ci
            """)

            # ------------------------------------------------
            # DỮ LIỆU ĐIỂM ĐẾN MẪU
            # ------------------------------------------------

            cursor.execute("""
                SELECT COUNT(*) AS total
                FROM destinations
            """)

            destination_count = cursor.fetchone()["total"]

            if destination_count == 0:

                destinations = [

                    (
                        "Thích Ca Phật Đài",
                        "Vũng Tàu",
                        "Tâm linh",
                        1000,
                        800,
                        "Điểm tham quan tâm linh nổi tiếng tại Vũng Tàu",
                        "Hoạt động"
                    ),

                    (
                        "Bãi Sau Vũng Tàu",
                        "Vũng Tàu",
                        "Biển",
                        5000,
                        4000,
                        "Khu vực biển có lượng khách cao",
                        "Hoạt động"
                    ),

                    (
                        "Hồ Mây Park",
                        "Vũng Tàu",
                        "Vui chơi",
                        3000,
                        2400,
                        "Khu vui chơi và du lịch sinh thái",
                        "Hoạt động"
                    ),

                    (
                        "Khu du lịch Bình Châu",
                        "Xuyên Mộc",
                        "Sinh thái",
                        2500,
                        2000,
                        "Khu du lịch sinh thái và nghỉ dưỡng",
                        "Hoạt động"
                    ),

                    (
                        "Long Hải",
                        "Long Điền",
                        "Biển",
                        3500,
                        2800,
                        "Điểm du lịch biển và nghỉ dưỡng",
                        "Hoạt động"
                    ),

                    (
                        "Hồ Tràm",
                        "Xuyên Mộc",
                        "Nghỉ dưỡng",
                        4000,
                        3200,
                        "Khu vực nghỉ dưỡng ven biển",
                        "Hoạt động"
                    )
                ]

                cursor.executemany("""
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

                    VALUES
                    (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                """, destinations)

            # ------------------------------------------------
            # KHUNG GIỜ MẪU
            # ------------------------------------------------

            cursor.execute("""
                SELECT COUNT(*) AS total
                FROM time_slots
            """)

            slot_count = cursor.fetchone()["total"]

            if slot_count == 0:

                slots = [

                    (
                        "Sáng sớm",
                        "06:00:00",
                        "09:00:00",
                        1000
                    ),

                    (
                        "Buổi sáng",
                        "09:00:00",
                        "12:00:00",
                        1500
                    ),

                    (
                        "Buổi trưa",
                        "12:00:00",
                        "14:00:00",
                        1000
                    ),

                    (
                        "Buổi chiều",
                        "14:00:00",
                        "17:00:00",
                        1500
                    ),

                    (
                        "Buổi tối",
                        "17:00:00",
                        "21:00:00",
                        2000
                    )
                ]

                cursor.executemany("""
                    INSERT INTO time_slots
                    (
                        slot_name,
                        start_time,
                        end_time,
                        max_people
                    )

                    VALUES
                    (
                        %s,
                        %s,
                        %s,
                        %s
                    )
                """, slots)

        connection.commit()

        return True

    except Exception as e:

        if connection:
            connection.rollback()

        st.error(
            "❌ Không thể khởi tạo Database MySQL."
        )

        st.error(
            str(e)
        )

        return False


# ============================================================
# 6. KIỂM TRA KẾT NỐI
# ============================================================

def test_database():

    try:

        connection = get_connection()

        with connection.cursor() as cursor:

            cursor.execute(
                "SELECT VERSION() AS version"
            )

            result = cursor.fetchone()

        return result["version"]

    except Exception:

        return None


# ============================================================
# 7. KHỞI TẠO
# ============================================================

database_ready = initialize_database()

if not database_ready:

    st.stop()


# ============================================================
# 8. CÁC HÀM LẤY DỮ LIỆU
# ============================================================

def get_destinations():

    data = execute_query("""
        SELECT
            id,
            name,
            location,
            category,
            capacity,
            warning_level,
            description,
            status,
            created_at

        FROM destinations

        ORDER BY name
    """, fetch=True)

    if data is None:
        return pd.DataFrame()

    return pd.DataFrame(data)


def get_time_slots():

    data = execute_query("""
        SELECT
            id,
            slot_name,
            start_time,
            end_time,
            max_people

        FROM time_slots

        ORDER BY start_time
    """, fetch=True)

    if data is None:
        return pd.DataFrame()

    return pd.DataFrame(data)


def get_visits():

    data = execute_query("""
        SELECT

            v.id,

            d.name AS destination,

            d.location,

            d.category,

            v.visitor_name,

            v.visitor_group,

            v.number_of_people,

            v.visit_date,

            v.visit_time,

            v.time_slot,

            v.status,

            v.created_at

        FROM visits v

        INNER JOIN destinations d

            ON v.destination_id = d.id

        ORDER BY
            v.visit_date DESC,
            v.visit_time DESC,
            v.id DESC
    """, fetch=True)

    if data is None:
        return pd.DataFrame()

    return pd.DataFrame(data)


# ============================================================
# 9. TÍNH LƯỢNG KHÁCH
# ============================================================

def get_today_visitors():

    today = date.today()

    result = execute_query("""
        SELECT
            COALESCE(
                SUM(number_of_people),
                0
            ) AS total

        FROM visits

        WHERE visit_date = %s

        AND status != 'Đã hủy'
    """, (today,), fetch=True)

    if not result:
        return 0

    return int(result[0]["total"] or 0)


def get_destination_visitors(
    destination_id,
    selected_date=None
):

    if selected_date is None:
        selected_date = date.today()

    result = execute_query("""
        SELECT

            COALESCE(
                SUM(number_of_people),
                0
            ) AS total

        FROM visits

        WHERE destination_id = %s

        AND visit_date = %s

        AND status != 'Đã hủy'
    """, (
        destination_id,
        selected_date
    ), fetch=True)

    if not result:
        return 0

    return int(result[0]["total"] or 0)


def get_slot_visitors(
    destination_id,
    slot_name,
    selected_date=None
):

    if selected_date is None:
        selected_date = date.today()

    result = execute_query("""
        SELECT

            COALESCE(
                SUM(number_of_people),
                0
            ) AS total

        FROM visits

        WHERE destination_id = %s

        AND time_slot = %s

        AND visit_date = %s

        AND status != 'Đã hủy'
    """, (
        destination_id,
        slot_name,
        selected_date
    ), fetch=True)

    if not result:
        return 0

    return int(result[0]["total"] or 0)


# ============================================================
# 10. PHÂN LOẠI MỨC ĐỘ QUÁ TẢI
# ============================================================

def get_load_status(
    current,
    warning,
    capacity
):

    if capacity <= 0:
        return "⚫ Không xác định"

    percentage = (
        current / capacity * 100
    )

    if percentage >= 100:

        return "🔴 QUÁ TẢI"

    elif percentage >= 80:

        return "🟠 CAO"

    elif percentage >= 50:

        return "🟡 TRUNG BÌNH"

    else:

        return "🟢 THẤP"


def get_percentage(
    current,
    capacity
):

    if capacity <= 0:
        return 0

    return min(
        current / capacity,
        1
    )


# ============================================================
# 11. THÊM LƯỢT KHÁCH
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

    result = execute_query("""
        INSERT INTO visits
        (
            destination_id,
            visitor_name,
            visitor_group,
            number_of_people,
            visit_date,
            visit_time,
            time_slot,
            status
        )

        VALUES
        (
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            'Đã ghi nhận'
        )
    """, (
        destination_id,
        visitor_name,
        visitor_group,
        number_of_people,
        visit_date,
        visit_time,
        time_slot
    ))

    return result is not None


# ============================================================
# 12. HỦY LƯỢT KHÁCH
# ============================================================

def cancel_visit(visit_id):

    result = execute_query("""
        UPDATE visits

        SET status = 'Đã hủy'

        WHERE id = %s
    """, (visit_id,))

    return result is not None


# ============================================================
# 13. THÊM ĐIỂM ĐẾN
# ============================================================

def add_destination(
    name,
    location,
    category,
    capacity,
    warning_level,
    description
):

    result = execute_query("""
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

        VALUES
        (
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            'Hoạt động'
        )
    """, (
        name,
        location,
        category,
        capacity,
        warning_level,
        description
    ))

    return result is not None


# ============================================================
# 14. SIDEBAR
# ============================================================

st.sidebar.title("🌍 DESTINATION")
st.sidebar.title("FLOW MANAGER")

st.sidebar.caption(
    "Quản lý và giảm tải khách tại điểm đến"
)

st.sidebar.divider()

menu = st.sidebar.radio(
    "📌 CHỨC NĂNG",
    [
        "📊 Dashboard",
        "🚦 Giám sát điểm đến",
        "👥 Ghi nhận khách",
        "📅 Phân luồng theo giờ",
        "📍 Quản lý điểm đến",
        "📋 Lịch sử lượt khách",
        "🗄️ Database"
    ]
)

st.sidebar.divider()

st.sidebar.success(
    "🟢 MySQL Aiven đang được sử dụng"
)


# ============================================================
# 15. DASHBOARD
# ============================================================

if menu == "📊 Dashboard":

    st.title("🌍 Destination Flow Manager")

    st.caption(
        "Hệ thống quản lý, giám sát và điều phối "
        "lượng khách tại điểm đến du lịch"
    )

    destinations = get_destinations()

    if destinations.empty:

        st.warning(
            "Chưa có dữ liệu điểm đến."
        )

        st.stop()

    today_visitors = get_today_visitors()

    total_capacity = int(
        destinations["capacity"].sum()
    )

    active_destinations = len(
        destinations[
            destinations["status"] == "Hoạt động"
        ]
    )

    overloaded = 0
    high_load = 0

    for _, row in destinations.iterrows():

        current = get_destination_visitors(
            row["id"]
        )

        if current >= row["capacity"]:

            overloaded += 1

        elif (
            current >=
            row["warning_level"]
        ):

            high_load += 1

    # --------------------------------------------------------
    # KPI
    # --------------------------------------------------------

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric(
        "👥 KHÁCH HÔM NAY",
        f"{today_visitors:,}"
    )

    col2.metric(
        "📍 ĐIỂM ĐẾN",
        active_destinations
    )

    col3.metric(
        "🏟️ TỔNG SỨC CHỨA",
        f"{total_capacity:,}"
    )

    total_usage = (
        today_visitors /
        total_capacity *
        100
        if total_capacity > 0
        else 0
    )

    col4.metric(
        "📈 MỨC SỬ DỤNG",
        f"{total_usage:.1f}%"
    )

    col5.metric(
        "🔴 ĐIỂM QUÁ TẢI",
        overloaded
    )

    st.divider()

    # --------------------------------------------------------
    # CẢNH BÁO
    # --------------------------------------------------------

    st.subheader(
        "🚨 TRUNG TÂM CẢNH BÁO"
    )

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
                f"🔴 **{row['name']}** đang quá tải: "
                f"**{current:,}/{row['capacity']:,} khách**."
            )

        elif "CAO" in status:

            warning_found = True

            st.warning(
                f"🟠 **{row['name']}** đang có lượng khách cao: "
                f"**{current:,}/{row['capacity']:,} khách**."
            )

    if not warning_found:

        st.success(
            "🟢 Hiện chưa phát hiện điểm đến có nguy cơ quá tải."
        )

    st.divider()

    # --------------------------------------------------------
    # BẢNG ĐIỂM ĐẾN
    # --------------------------------------------------------

    st.subheader(
        "📍 TÌNH TRẠNG ĐIỂM ĐẾN"
    )

    dashboard_data = []

    for _, row in destinations.iterrows():

        current = get_destination_visitors(
            row["id"]
        )

        percentage = (
            current /
            row["capacity"] *
            100
            if row["capacity"] > 0
            else 0
        )

        status = get_load_status(
            current,
            row["warning_level"],
            row["capacity"]
        )

        dashboard_data.append({

            "Điểm đến":
                row["name"],

            "Khu vực":
                row["location"],

            "Loại hình":
                row["category"],

            "Khách hôm nay":
                current,

            "Sức chứa":
                row["capacity"],

            "Mức sử dụng":
                f"{percentage:.1f}%",

            "Trạng thái":
                status
        })

    dashboard_df = pd.DataFrame(
        dashboard_data
    )

    st.dataframe(
        dashboard_df,
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    # --------------------------------------------------------
    # BIỂU ĐỒ
    # --------------------------------------------------------

    st.subheader(
        "📊 LƯỢNG KHÁCH THEO ĐIỂM ĐẾN"
    )

    chart_df = dashboard_df[
        [
            "Điểm đến",
            "Khách hôm nay"
        ]
    ].set_index(
        "Điểm đến"
    )

    st.bar_chart(
        chart_df
    )

    st.divider()

    # --------------------------------------------------------
    # ĐIỀU PHỐI
    # --------------------------------------------------------

    st.subheader(
        "🧭 GỢI Ý ĐIỀU PHỐI"
    )

    high_destinations = []
    available_destinations = []

    for _, row in destinations.iterrows():

        current = get_destination_visitors(
            row["id"]
        )

        percentage = (
            current /
            row["capacity"]
            if row["capacity"] > 0
            else 0
        )

        if percentage >= 0.8:

            high_destinations.append(
                row["name"]
            )

        elif percentage < 0.5:

            available_destinations.append(
                row["name"]
            )

    if high_destinations:

        st.warning(
            "⚠️ Nên kiểm soát lượng khách tại: "
            + ", ".join(high_destinations)
        )

    if available_destinations:

        st.info(
            "🟢 Các điểm còn khả năng tiếp nhận khách: "
            + ", ".join(available_destinations)
        )

    if not high_destinations:

        st.success(
            "🟢 Chưa có điểm đến nào vượt ngưỡng điều phối."
        )


# ============================================================
# 16. GIÁM SÁT ĐIỂM ĐẾN
# ============================================================

elif menu == "🚦 Giám sát điểm đến":

    st.title(
        "🚦 Giám sát sức chứa điểm đến"
    )

    destinations = get_destinations()

    if destinations.empty:

        st.warning(
            "Chưa có điểm đến."
        )

        st.stop()

    selected_name = st.selectbox(
        "📍 Chọn điểm đến",
        destinations["name"].tolist()
    )

    destination = destinations[
        destinations["name"] ==
        selected_name
    ].iloc[0]

    selected_date = st.date_input(
        "📅 Ngày theo dõi",
        value=date.today()
    )

    current = get_destination_visitors(
        destination["id"],
        selected_date
    )

    percentage = (
        current /
        destination["capacity"] *
        100
        if destination["capacity"] > 0
        else 0
    )

    status = get_load_status(
        current,
        destination["warning_level"],
        destination["capacity"]
    )

    # --------------------------------------------------------
    # KPI
    # --------------------------------------------------------

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "👥 LƯỢT KHÁCH",
        f"{current:,}"
    )

    c2.metric(
        "🏟️ SỨC CHỨA",
        f"{destination['capacity']:,}"
    )

    c3.metric(
        "📈 SỬ DỤNG",
        f"{percentage:.1f}%"
    )

    c4.metric(
        "🚦 TRẠNG THÁI",
        status
    )

    st.divider()

    # --------------------------------------------------------
    # PROGRESS
    # --------------------------------------------------------

    st.subheader(
        "📊 MỨC SỬ DỤNG SỨC CHỨA"
    )

    st.progress(
        get_percentage(
            current,
            destination["capacity"]
        )
    )

    if percentage >= 100:

        st.error(
            "🔴 ĐIỂM ĐẾN ĐANG QUÁ TẢI"
        )

        st.warning(
            "Cần hạn chế tiếp nhận thêm khách "
            "và cân nhắc phân luồng sang thời gian "
            "hoặc điểm đến khác."
        )

    elif percentage >= 80:

        st.warning(
            "🟠 Điểm đến gần mức quá tải."
        )

    elif percentage >= 50:

        st.info(
            "🟡 Lượng khách ở mức trung bình."
        )

    else:

        st.success(
            "🟢 Điểm đến còn nhiều khả năng tiếp nhận."
        )

    st.divider()

    # --------------------------------------------------------
    # KHUNG GIỜ
    # --------------------------------------------------------

    st.subheader(
        "⏰ PHÂN BỐ KHÁCH THEO KHUNG GIỜ"
    )

    slots = get_time_slots()

    slot_data = []

    for _, slot in slots.iterrows():

        visitors = get_slot_visitors(
            destination["id"],
            slot["slot_name"],
            selected_date
        )

        percentage_slot = (
            visitors /
            slot["max_people"] *
            100
            if slot["max_people"] > 0
            else 0
        )

        if percentage_slot >= 100:

            slot_status = "🔴 Đầy"

        elif percentage_slot >= 80:

            slot_status = "🟠 Gần đầy"

        elif percentage_slot >= 50:

            slot_status = "🟡 Trung bình"

        else:

            slot_status = "🟢 Còn chỗ"

        slot_data.append({

            "Khung giờ":
                slot["slot_name"],

            "Thời gian":
                f"{slot['start_time']} - "
                f"{slot['end_time']}",

            "Khách":
                visitors,

            "Giới hạn":
                slot["max_people"],

            "Sử dụng":
                f"{percentage_slot:.1f}%",

            "Trạng thái":
                slot_status
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
        slot_df.set_index(
            "Khung giờ"
        )[["Khách"]]
    )


# ============================================================
# 17. GHI NHẬN KHÁCH
# ============================================================

elif menu == "👥 Ghi nhận khách":

    st.title(
        "👥 Ghi nhận lượt khách"
    )

    st.info(
        "Nhập thông tin khách/đoàn khách. "
        "Dữ liệu sẽ được lưu trực tiếp vào MySQL Aiven."
    )

    destinations = get_destinations()

    if destinations.empty:

        st.warning(
            "Chưa có điểm đến."
        )

        st.stop()

    with st.form(
        "visitor_form",
        clear_on_submit=True
    ):

        destination_name = st.selectbox(
            "📍 Điểm đến *",
            destinations["name"].tolist()
        )

        destination = destinations[
            destinations["name"] ==
            destination_name
        ].iloc[0]

        col1, col2 = st.columns(2)

        with col1:

            visitor_name = st.text_input(
                "👤 Người đại diện",
                placeholder="Nguyễn Văn A"
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
                "👥 Số lượng người *",
                min_value=1,
                max_value=10000,
                value=1
            )

            visit_date = st.date_input(
                "📅 Ngày đến",
                value=date.today()
            )

            visit_time = st.time_input(
                "⏰ Thời gian đến",
                value=datetime.now().time()
            )

        slots = get_time_slots()

        time_slot = st.selectbox(
            "🕐 Khung giờ",
            slots["slot_name"].tolist()
        )

        submitted = st.form_submit_button(
            "✅ GHI NHẬN LƯỢT KHÁCH",
            type="primary",
            use_container_width=True
        )

        if submitted:

            if number_of_people <= 0:

                st.error(
                    "Số lượng người phải lớn hơn 0."
                )

            else:

                current = get_destination_visitors(
                    destination["id"],
                    visit_date
                )

                new_total = (
                    current +
                    number_of_people
                )

                capacity = destination[
                    "capacity"
                ]

                if new_total > capacity:

                    st.error(
                        f"🔴 CẢNH BÁO QUÁ TẢI!\n\n"
                        f"Hiện tại: {current:,} khách\n\n"
                        f"Đoàn mới: {number_of_people:,} khách\n\n"
                        f"Sau khi ghi nhận: "
                        f"{new_total:,} khách\n\n"
                        f"Sức chứa: "
                        f"{capacity:,} khách"
                    )

                    confirm = st.checkbox(
                        "⚠️ Tôi xác nhận vẫn muốn ghi nhận đoàn khách này."
                    )

                    if confirm:

                        success = add_visit(
                            destination["id"],
                            visitor_name,
                            visitor_group,
                            number_of_people,
                            visit_date,
                            visit_time,
                            time_slot
                        )

                        if success:

                            st.success(
                                "✅ Đã ghi nhận lượt khách."
                            )

                            st.rerun()

                else:

                    success = add_visit(
                        destination["id"],
                        visitor_name,
                        visitor_group,
                        number_of_people,
                        visit_date,
                        visit_time,
                        time_slot
                    )

                    if success:

                        remaining = (
                            capacity -
                            new_total
                        )

                        st.success(
                            "✅ Ghi nhận khách thành công!"
                        )

                        st.info(
                            f"Điểm đến còn khoảng "
                            f"**{remaining:,} người** "
                            "theo sức chứa thiết lập."
                        )

                        st.rerun()


# ============================================================
# 18. PHÂN LUỒNG THEO GIỜ
# ============================================================

elif menu == "📅 Phân luồng theo giờ":

    st.title(
        "📅 Điều phối khách theo khung giờ"
    )

    st.write(
        "Theo dõi số khách theo từng khung giờ "
        "để hạn chế tình trạng tập trung quá đông."
    )

    destinations = get_destinations()
    slots = get_time_slots()

    if destinations.empty:

        st.warning(
            "Chưa có điểm đến."
        )

        st.stop()

    selected_name = st.selectbox(
        "📍 Điểm đến",
        destinations["name"].tolist()
    )

    destination = destinations[
        destinations["name"] ==
        selected_name
    ].iloc[0]

    selected_date = st.date_input(
        "📅 Ngày",
        value=date.today()
    )

    st.divider()

    data = []

    for _, slot in slots.iterrows():

        visitors = get_slot_visitors(
            destination["id"],
            slot["slot_name"],
            selected_date
        )

        limit = slot["max_people"]

        percentage = (
            visitors /
            limit *
            100
            if limit > 0
            else 0
        )

        if percentage >= 100:

            status = "🔴 ĐẦY"

        elif percentage >= 80:

            status = "🟠 GẦN ĐẦY"

        elif percentage >= 50:

            status = "🟡 TRUNG BÌNH"

        else:

            status = "🟢 CÒN NHIỀU CHỖ"

        data.append({

            "Khung giờ":
                slot["slot_name"],

            "Thời gian":
                f"{slot['start_time']} - "
                f"{slot['end_time']}",

            "Khách":
                visitors,

            "Giới hạn":
                limit,

            "Mức sử dụng":
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
        "🧭 KHUYẾN NGHỊ ĐIỀU PHỐI"
    )

    for _, row in slot_df.iterrows():

        if row["Trạng thái"] == "🔴 ĐẦY":

            st.error(
                f"🔴 **{row['Khung giờ']}** đã đạt giới hạn. "
                "Nên hạn chế tiếp nhận thêm khách."
            )

        elif row["Trạng thái"] == "🟠 GẦN ĐẦY":

            st.warning(
                f"🟠 **{row['Khung giờ']}** gần đầy. "
                "Nên khuyến khích khách chuyển sang khung giờ khác."
            )

        elif row["Trạng thái"] == "🟢 CÒN NHIỀU CHỖ":

            st.success(
                f"🟢 **{row['Khung giờ']}** còn nhiều khả năng "
                "tiếp nhận khách."
            )

    st.divider()

    st.subheader(
        "💡 MÔ HÌNH PHÂN LUỒNG"
    )

    st.markdown(
        """
        **Điểm đến quá đông**

        🔴 Phát hiện quá tải  
        ↓  
        🟠 Cảnh báo nhân viên điều phối  
        ↓  
        🕐 Đề xuất khung giờ ít khách  
        ↓  
        📍 Xem xét điểm đến thay thế  
        ↓  
        🟢 Phân tán dòng khách  
        ↓  
        📊 Theo dõi lại dữ liệu
        """
    )


# ============================================================
# 19. QUẢN LÝ ĐIỂM ĐẾN
# ============================================================

elif menu == "📍 Quản lý điểm đến":

    st.title(
        "📍 Quản lý điểm đến"
    )

    destinations = get_destinations()

    if not destinations.empty:

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

    st.subheader(
        "➕ Thêm điểm đến"
    )

    with st.form(
        "destination_form",
        clear_on_submit=True
    ):

        name = st.text_input(
            "Tên điểm đến *"
        )

        location = st.text_input(
            "Khu vực *"
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
                "🏟️ Sức chứa tối đa",
                min_value=1,
                value=1000
            )

        with col2:

            warning_level = st.number_input(
                "⚠️ Ngưỡng cảnh báo",
                min_value=1,
                value=800
            )

        description = st.text_area(
            "Mô tả"
        )

        submitted = st.form_submit_button(
            "➕ THÊM ĐIỂM ĐẾN",
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

            elif warning_level >= capacity:

                st.error(
                    "Ngưỡng cảnh báo nên nhỏ hơn sức chứa."
                )

            else:

                success = add_destination(
                    name.strip(),
                    location.strip(),
                    category,
                    capacity,
                    warning_level,
                    description.strip()
                )

                if success:

                    st.success(
                        f"✅ Đã thêm điểm đến: {name}"
                    )

                    st.rerun()


# ============================================================
# 20. LỊCH SỬ LƯỢT KHÁCH
# ============================================================

elif menu == "📋 Lịch sử lượt khách":

    st.title(
        "📋 Lịch sử lượt khách"
    )

    visits = get_visits()

    if visits.empty:

        st.info(
            "Chưa có dữ liệu lượt khách."
        )

    else:

        # ----------------------------------------------------
        # BỘ LỌC
        # ----------------------------------------------------

        col1, col2, col3 = st.columns(3)

        with col1:

            destinations_filter = [
                "Tất cả"
            ] + sorted(
                visits["destination"]
                .dropna()
                .unique()
                .tolist()
            )

            destination_filter = st.selectbox(
                "📍 Điểm đến",
                destinations_filter
            )

        with col2:

            group_filter = st.selectbox(
                "👥 Loại khách",
                [
                    "Tất cả"
                ] + sorted(
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
            pd.to_datetime(
                filtered["visit_date"]
            ).dt.date
            == date_filter
        ]

        # ----------------------------------------------------
        # KPI
        # ----------------------------------------------------

        total_people = int(
            filtered[
                "number_of_people"
            ].sum()
        )

        total_groups = len(
            filtered
        )

        c1, c2 = st.columns(2)

        c1.metric(
            "👥 TỔNG KHÁCH",
            f"{total_people:,}"
        )

        c2.metric(
            "🎫 SỐ LƯỢT GHI NHẬN",
            total_groups
        )

        st.divider()

        # ----------------------------------------------------
        # BẢNG
        # ----------------------------------------------------

        show_columns = [

            "id",
            "destination",
            "visitor_name",
            "visitor_group",
            "number_of_people",
            "visit_date",
            "visit_time",
            "time_slot",
            "status"
        ]

        st.dataframe(
            filtered[show_columns],
            use_container_width=True,
            hide_index=True
        )

        # ----------------------------------------------------
        # HỦY LƯỢT KHÁCH
        # ----------------------------------------------------

        st.divider()

        st.subheader(
            "🗑️ Hủy lượt ghi nhận"
        )

        active_visits = filtered[
            filtered["status"] != "Đã hủy"
        ]

        if not active_visits.empty:

            visit_options = {}

            for _, row in active_visits.iterrows():

                label = (
                    f"#{row['id']} - "
                    f"{row['destination']} - "
                    f"{row['visitor_name']} - "
                    f"{row['number_of_people']} người"
                )

                visit_options[
                    label
                ] = int(row["id"])

            selected_visit = st.selectbox(
                "Chọn lượt cần hủy",
                list(
                    visit_options.keys()
                )
            )

            if st.button(
                "🗑️ HỦY LƯỢT KHÁCH",
                type="secondary"
            ):

                visit_id = visit_options[
                    selected_visit
                ]

                if cancel_visit(
                    visit_id
                ):

                    st.success(
                        "Đã hủy lượt ghi nhận."
                    )

                    st.rerun()

        st.divider()

        # ----------------------------------------------------
        # DOWNLOAD CSV
        # ----------------------------------------------------

        csv = filtered.to_csv(
            index=False
        ).encode(
            "utf-8-sig"
        )

        st.download_button(
            "⬇️ XUẤT DỮ LIỆU CSV",
            data=csv,
            file_name=(
                "visitor_data_"
                + date_filter.strftime(
                    "%Y%m%d"
                )
                + ".csv"
            ),
            mime="text/csv"
        )


# ============================================================
# 21. DATABASE
# ============================================================

elif menu == "🗄️ Database":

    st.title(
        "🗄️ Thông tin Database"
    )

    st.info(
        "Trang này dùng để kiểm tra trạng thái "
        "kết nối giữa Streamlit và Aiven MySQL."
    )

    version = test_database()

    if version:

        st.success(
            "🟢 KẾT NỐI MYSQL THÀNH CÔNG"
        )

        col1, col2 = st.columns(2)

        with col1:

            st.metric(
                "Database",
                DB_NAME
            )

            st.metric(
                "User",
                DB_USER
            )

        with col2:

            st.metric(
                "Port",
                DB_PORT
            )

            st.metric(
                "MySQL Version",
                version
            )

        st.divider()

        st.subheader(
            "📊 Thống kê Database"
        )

        destinations = get_destinations()

        visits = get_visits()

        slots = get_time_slots()

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "📍 Điểm đến",
            len(destinations)
        )

        c2.metric(
            "👥 Lượt ghi nhận",
            len(visits)
        )

        c3.metric(
            "⏰ Khung giờ",
            len(slots)
        )

        st.divider()

        st.subheader(
            "🗃️ Các bảng đang sử dụng"
        )

        st.write(
            """
            **destinations**
            - Lưu thông tin điểm đến
            - Sức chứa
            - Ngưỡng cảnh báo
            - Trạng thái

            **visits**
            - Lưu từng lượt khách
            - Số lượng người
            - Ngày/giờ đến
            - Khung giờ
            - Loại khách

            **time_slots**
            - Quản lý các khung giờ
            - Giới hạn khách theo khung giờ
            """
        )

        st.divider()

        st.success(
            "Dữ liệu hiện đang được lưu trực tiếp "
            "trên Aiven MySQL."
        )

    else:

        st.error(
            "🔴 KHÔNG KẾT NỐI ĐƯỢC MYSQL"
        )

        st.write(
            "Hãy kiểm tra Host, Port, Username, "
            "Password và trạng thái Aiven service."
        )


# ============================================================
# 22. FOOTER
# ============================================================

st.sidebar.divider()

st.sidebar.caption(
    "🌍 Destination Flow Manager"
)

st.sidebar.caption(
    "MySQL • Aiven • Streamlit"
)

st.sidebar.caption(
    "Quản lý • Giám sát • Cảnh báo • Phân luồng"
)
