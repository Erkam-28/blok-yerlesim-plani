st.write("SAHALAR kontrolü:")
for s in SAHALAR:
    try:
        u, g = s["alan"](datetime.now())
        st.write(f"✅ {s['ad']}: {u} x {g}")
    except Exception as e:
        st.error(f"❌ {s['ad']} HATALI: {e}")
