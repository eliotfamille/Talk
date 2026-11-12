import asyncio
import tornado.web
from tornado.escape import json_decode
from tornado.ioloop import IOLoop
import ai_client, conversation
from schemas import Request
from config import Provider


class BaseHandler(tornado.web.RequestHandler):
    def erreur(self, code, detail):     # reponse d'erreur en json
        self.set_status(code)
        raise tornado.web.Finish({"detail": detail})  # termine sans write_error

    def corps_json(self):   # lit le json du corps
        try:
            data = json_decode(self.request.body)
        except ValueError:
            self.erreur(400, "JSON invalide")
        if not isinstance(data, dict):
            self.erreur(422, "Objet JSON attendu")
        return data

    def lire_provider(self, valeur, requis=False):  # texte vers Provider
        if valeur is None:
            if requis:
                self.erreur(422, "provider requis")
            return None
        try:
            return Provider(valeur)
        except ValueError:
            self.erreur(422, "provider invalide")

    def lire_texte(self, data, nom):    # champ texte obligatoire
        valeur = data.get(nom)
        if not isinstance(valeur, str) or not valeur:
            self.erreur(422, f"{nom} requis")
        return valeur

    def write_error(self, status_code, **kwargs):   # erreurs tornado en json
        self.write({"detail": f"Erreur {status_code}"})


class RacineHandler(BaseHandler):
    def get(self):
        self.write({"Status": "OK"})


class ChatHandler(BaseHandler):     # /chat
    async def post(self):
        data = self.corps_json()
        requete = Request(
            message=self.lire_texte(data, "message"),
            provider=self.lire_provider(data.get("provider")),
            model=data.get("model"),
            conversation_id=data.get("conversation_id"),
        )
        reponse, conv_id = await IOLoop.current().run_in_executor(
            None, ai_client.repondre_with_history, requete)     # appel bloquant, fil separe
        self.write({"reponse": reponse, "conversation_id": conv_id})


class CleHandler(BaseHandler):  # /config/cle
    def post(self):
        data = self.corps_json()
        cle = self.lire_texte(data, "cle")
        provider = self.lire_provider(data.get("provider"), requis=True)
        ai_client.api(cle, provider)  # configurer cle api
        self.write({"Status": "OK"})


class ModelesHandler(BaseHandler):  # /models
    async def get(self):
        provider = self.lire_provider(self.get_query_argument("provider", None))    # lu dans la query
        try:
            modeles = await IOLoop.current().run_in_executor(
                None, ai_client.list_model, provider)   # appel bloquant, fil separe
        except RuntimeError as e:
            self.erreur(400, str(e))
        except Exception:
            self.erreur(502, "Impossible de lister les modeles")  # erreur liste modeles
        self.write({
            "modeles": modeles,  # liste modeles
            "actuel": ai_client.get_model(),  # modele actif
            "provider": ai_client.get_provider().value,  # provider actif
        })


class ModeleHandler(BaseHandler):   # /config/modele
    def post(self):
        data = self.corps_json()
        modele = self.lire_texte(data, "modele")
        provider = self.lire_provider(data.get("provider"), requis=True)
        ai_client.set_model(modele, provider)  # changer modele
        self.write({"status": "ok"})


class ProviderHandler(BaseHandler):     # /config/provider
    def post(self):
        provider = self.lire_provider(self.get_query_argument("provider"))    # lu dans la query
        ai_client.set_provider(provider)  # changer provider
        self.write({"status": "ok", "provider": provider.value})

    def get(self):
        self.write({"provider": ai_client.get_provider().value})  # get provider actif


class ConversationsHandler(BaseHandler):    # /conversations
    def get(self):
        self.write({"conversations": conversation.list_conversations()})   # liste conversations


class ConversationHandler(BaseHandler):     # /conversations/id
    def delete(self, conv_id):
        if conversation.delete_conversation(conv_id):
            self.write({"status": "ok"})
        else:
            self.erreur(404, "Conversation non trouvee")


def make_app():     # table des routes
    return tornado.web.Application([
        (r"/", RacineHandler),
        (r"/chat", ChatHandler),
        (r"/config/cle", CleHandler),
        (r"/models", ModelesHandler),
        (r"/config/modele", ModeleHandler),
        (r"/config/provider", ProviderHandler),
        (r"/conversations", ConversationsHandler),
        (r"/conversations/([^/]+)", ConversationHandler),
    ])


async def main():
    app = make_app()
    app.listen(8000, address="127.0.0.1")   # port 8000, local seulement
    await asyncio.Event().wait()    # garde le serveur actif


if __name__ == "__main__":
    asyncio.run(main())
