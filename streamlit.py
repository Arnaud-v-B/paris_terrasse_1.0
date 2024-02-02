import streamlit as st
from shadow_mapper.main import *

st.title("TRSS: Trouvez votre bonheur au soleil")
st.write("Brought to by YNS")

entry_text = st.text_input("Ecrivez votre position ici, pensez à bien ajouter l'arrondissement", placeholder="Pl. de la République, 75010 Paris, France")
if st.button("Trouvez moi une pinte au soleil"):
    address = entry_text

    # Show spinner while waiting for API response
    @st.cache_data
    with st.spinner("Sous le soleil 🌞 Bleu marine et blue 🌞 Ebloui pareil"):
        best = tarrasse(address=entry_text)
    if len(best)==0:
        st.write("On ne peut pas vous trouver de terrasse :( re-essayez avec d'autre parametres")
    else:
        best = best[["Numéro et voie", "Nom de la société", "dist_from_usr(km)"]]
        best["Distance"] = best["dist_from_usr(km)"].apply(lambda x : round(x * 100, 0))
        st.DataFrame(best)
