import streamlit as st
import api_client

PROVIDERS = ["openai", "google", "nvidia"]  # fournisseurs disponibles

st.title("Talk")

if "messages" not in st.session_state:
    st.session_state.messages = []  # historique affiche
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None  # conversation active
if "provider" not in st.session_state:
    try:
        st.session_state.provider = api_client.get_provider()  # provider du backend
    except Exception:
        st.session_state.provider = "nvidia"  # defaut si backend absent


def notifier(type_, texte):     # message affiche au prochain rendu
    st.session_state.notice = (type_, texte)


def changer_provider():     # callback selectbox provider
    try:
        api_client.definir_provider(st.session_state.provider)
        notifier("success", f"Fournisseur change : {st.session_state.provider}")
    except Exception as e:
        notifier("error", f"[erreur] {e}")
    if "modeles" in st.session_state:
        del st.session_state["modeles"]     # force le rechargement


def changer_modele():   # callback selectbox modele
    try:
        api_client.choisir_modele(st.session_state.modele, st.session_state.provider)
        notifier("success", f"Modele choisi : {st.session_state.modele}")
    except Exception as e:
        notifier("error", f"[erreur] {e}")


def nouvelle_conversation():    # callback bouton
    st.session_state.messages = []
    st.session_state.conversation_id = None


def charger_modeles():  # liste les modeles du provider actif
    try:
        with st.spinner("Chargement des modeles..."):
            data = api_client.lister_modeles(st.session_state.provider)
        st.session_state.modeles = data["modeles"]
        if data["modeles"]:
            actuel = data["actuel"]
            st.session_state.modele = actuel if actuel in data["modeles"] else data["modeles"][0]   # modele affiche
    except Exception as e:
        st.session_state.modeles = []
        notifier("error", f"[erreur modeles] {e}")


@st.dialog("Cle API")
def popup_cle():    # fenetre de saisie de la cle
    provider = st.selectbox("Fournisseur", PROVIDERS, index=PROVIDERS.index(st.session_state.provider))
    cle = st.text_input("Colle cle API", type="password")   # masque la saisie
    if st.button("Enregistrer"):
        if not cle.strip():
            st.error("Cle vide")
            return
        try:
            api_client.enregistreCle(cle.strip(), provider)
        except Exception as e:
            st.error(f"[erreur] {e}")
            return
        notifier("success", f"Cle API enregistree pour {provider}.")
        if "modeles" in st.session_state:
            del st.session_state["modeles"]     # recharge les modeles
        st.rerun()  # ferme la fenetre


with st.sidebar:    # bar gauche
    st.selectbox("Fournisseur", PROVIDERS, key="provider", on_change=changer_provider)
    if "modeles" not in st.session_state:
        charger_modeles()
    st.selectbox("Modele", st.session_state.modeles, key="modele", on_change=changer_modele)
    if st.button("Cle API", width="stretch"):
        popup_cle()
    st.button("Nouvelle conversation", on_click=nouvelle_conversation, width="stretch")
    if "notice" in st.session_state:
        type_, texte = st.session_state.notice
        if type_ == "error":
            st.error(texte)
        else:
            st.success(texte)
        del st.session_state["notice"]  # affiche une seule fois

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ecris un message"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Reflexion..."):
            try:
                modele = st.session_state.modele if st.session_state.modeles else None  # modele choisi
                data = api_client.envoyer(prompt, st.session_state.provider, modele, st.session_state.conversation_id)
                st.session_state.conversation_id = data["conversation_id"]  # garde l'id
                reponse = data["reponse"]
            except Exception as e:
                reponse = f"[erreur] {e}"
        st.markdown(reponse)
    st.session_state.messages.append({"role": "assistant", "content": reponse})
