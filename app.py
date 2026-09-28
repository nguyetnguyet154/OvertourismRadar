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
# FOOTER
# ============================================================

st.sidebar.divider()

st.sidebar.caption(
    "🌍 Destination Flow Manager"
)

st.sidebar.caption(
    "Quản lý • Giám sát • Cảnh báo • Phân luồng"
)
