import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
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
# 메인 화면 - ① 선택 지역의 연령별 인구 그래프
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

# =====================================================
# ② 인구구조가 가장 비슷한 지역 Top 5
# =====================================================
st.header("👯 인구구조가 가장 비슷한 지역 Top 5")
st.write(
    "여기서 말하는 '인구구조'는 **나이대별 인구 비율(연령 구성비)**을 뜻해요. "
    "지역 크기(전체 인구수)가 달라도, 나이대가 퍼져 있는 '모양'이 비슷하면 비슷한 지역으로 찾아드려요. "
    "(주의: 이 데이터는 시도·시군구 합계행도 함께 포함되어 있어서, 시도 단위 지역이 비교 대상에 섞일 수 있어요.)"
)

# '계_' 나이별 열만 모아서 비교에 사용해요.
total_cols = age_cols.get("계", {})
sorted_ages = sorted(total_cols.keys())
total_age_cols = [total_cols[a] for a in sorted_ages]

# 모든 지역의 나이별 인구를 행렬로 만들고, 지역별 합으로 나눠서 '비율'로 바꿔요.
age_matrix = df[total_age_cols].values.astype(float)
row_sums = age_matrix.sum(axis=1, keepdims=True)
row_sums[row_sums == 0] = 1  # 0으로 나누는 것 방지
ratio_matrix = age_matrix / row_sums

# 선택한 지역의 비율 벡터 찾기
selected_pos = df.index.get_loc(df.index[df["지역명"] == selected_region][0])
selected_vector = ratio_matrix[selected_pos]

# 유클리드 거리로 '얼마나 다른지' 계산 (거리가 작을수록 구조가 비슷해요)
distances = np.sqrt(((ratio_matrix - selected_vector) ** 2).sum(axis=1))

result_df = df[["지역명"]].copy()
result_df["거리"] = distances

# 자기 자신은 제외하고, 거리가 작은(=구조가 비슷한) 순서로 5개만 뽑아요.
result_df = result_df[result_df["지역명"] != selected_region]
top5 = result_df.sort_values("거리").head(5).reset_index(drop=True)

st.dataframe(
    top5.rename(columns={"거리": "구조 차이(작을수록 비슷함)"}),
    use_container_width=True,
    hide_index=True,
)

# --- 라인 그래프: 선택 지역 vs Top5 지역의 연령 구성비 비교 ---
fig_compare = go.Figure()

# 선택한 지역은 굵은 빨간 선으로 강조
fig_compare.add_trace(
    go.Scatter(
        x=sorted_ages,
        y=selected_vector * 100,  # 보기 편하게 %로 변환
        mode="lines",
        name=f"⭐ {selected_region} (선택 지역)",
        line=dict(width=4, color="#e74c3c"),
    )
)

# Top5 지역은 얇은 선으로 함께 표시
colors = ["#3498db", "#2ecc71", "#9b59b6", "#f39c12", "#1abc9c"]
for i, top_row in top5.iterrows():
    region_name = top_row["지역명"]
    pos = df.index.get_loc(df.index[df["지역명"] == region_name][0])
    vec = ratio_matrix[pos]
    fig_compare.add_trace(
        go.Scatter(
            x=sorted_ages,
            y=vec * 100,
            mode="lines",
            name=region_name,
            line=dict(width=2, color=colors[i % len(colors)]),
        )
    )

fig_compare.update_layout(
    title=f"'{selected_region}'과(와) 비슷한 지역들의 연령 구성비 비교",
    xaxis_title="연령 (세)",
    yaxis_title="비율 (%)",
    hovermode="x unified",
    height=550,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)

st.plotly_chart(fig_compare, use_container_width=True)

# --- 막대 그래프: Top5 유사도 순위 (거리가 작을수록 막대가 짧아요) ---
fig_rank = px.bar(
    top5,
    x="지역명",
    y="거리",
    labels={"지역명": "지역", "거리": "구조 차이 (작을수록 비슷함)"},
    title="Top 5 지역별 구조 차이 크기 비교",
    text_auto=".4f",
)
fig_rank.update_layout(yaxis_title="구조 차이 (작을수록 비슷함)")
st.plotly_chart(fig_rank, use_container_width=True)
