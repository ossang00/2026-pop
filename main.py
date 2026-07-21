import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re

st.set_page_config(page_title="연령별 인구 현황", layout="wide")

# -----------------------------
# 데이터 파일 (코드와 같은 폴더에 위치)
# -----------------------------
DATA_PATH = "202606_202606_연령별인구현황_월간.csv"


# -----------------------------
# 데이터 로드 & 전처리
# -----------------------------
@st.cache_data
def load_data(path):
    df = pd.read_csv(path, encoding="cp949")

    # 콤마 제거 후 숫자형 변환 (행정구역 컬럼 제외)
    for col in df.columns:
        if col != "행정구역":
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(",", "", regex=False)
                .replace("nan", "0")
                .astype(int)
            )

    # 행정구역명에서 괄호(코드) 제거 + 공백 정리
    df["지역명"] = df["행정구역"].str.replace(r"\s*\(\d+\)", "", regex=True).str.strip()

    return df


def parse_age_columns(columns):
    """컬럼명에서 성별/연령 추출: 2026년06월_계_0세, 2026년06월_남_10세 등"""
    pattern = re.compile(r"_(계|남|여)_(\d+|100세 이상)세?$")
    parsed = {}
    for col in columns:
        m = pattern.search(col)
        if m:
            gender = m.group(1)
            age_str = m.group(2)
            age = 100 if "100" in age_str else int(age_str)
            parsed.setdefault(gender, {})[age] = col
    return parsed


df = load_data(DATA_PATH)
age_cols = parse_age_columns(list(df.columns))

# -----------------------------
# 사이드바 - 지역 선택 (선택 + 직접 입력)
# -----------------------------
st.sidebar.header("🔎 지역 선택")

region_list = df["지역명"].tolist()

search_text = st.sidebar.text_input("지역명 검색 (일부만 입력해도 됩니다)", "")

if search_text:
    filtered_regions = [r for r in region_list if search_text.strip() in r]
else:
    filtered_regions = region_list

if not filtered_regions:
    st.sidebar.warning("검색 결과가 없습니다. 전체 목록에서 선택해주세요.")
    filtered_regions = region_list

selected_region = st.sidebar.selectbox(
    "지역 선택",
    options=filtered_regions,
    index=0,
)

gender_map = {"전체": "계", "남성": "남", "여성": "여"}
selected_gender_label = st.sidebar.radio("성별", list(gender_map.keys()), horizontal=True)
selected_gender = gender_map[selected_gender_label]

compare_gender = st.sidebar.checkbox("남/여 비교해서 함께 보기", value=False)

# -----------------------------
# 메인 화면
# -----------------------------
st.title("📊 연령별 인구 현황")
st.subheader(f"선택 지역: {selected_region}")

row = df[df["지역명"] == selected_region]

if row.empty:
    st.error("해당 지역 데이터를 찾을 수 없습니다.")
else:
    row = row.iloc[0]

    fig = go.Figure()

    def add_line(gender_code, label, color):
        cols = age_cols.get(gender_code, {})
        ages = sorted(cols.keys())
        values = [row[cols[a]] for a in ages]
        fig.add_trace(
            go.Scatter(
                x=ages,
                y=values,
                mode="lines",
                name=label,
                line=dict(width=2, color=color),
            )
        )

    if compare_gender:
        add_line("남", "남성", "#1f77b4")
        add_line("여", "여성", "#e377c2")
    else:
        color_map = {"계": "#2ca02c", "남": "#1f77b4", "여": "#e377c2"}
        add_line(selected_gender, selected_gender_label, color_map[selected_gender])

    fig.update_layout(
        xaxis_title="연령 (세)",
        yaxis_title="인구 수 (명)",
        hovermode="x unified",
        height=550,
        margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    st.plotly_chart(fig, use_container_width=True)

    with st.expander("원본 데이터 보기"):
        cols = age_cols.get(selected_gender, {})
        ages = sorted(cols.keys())
        table = pd.DataFrame(
            {"연령": ages, "인구수": [row[cols[a]] for a in ages]}
        )
        st.dataframe(table, use_container_width=True, hide_index=True)
