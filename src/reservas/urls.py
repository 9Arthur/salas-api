from rest_framework.routers import SimpleRouter

from reservas.views import SalaViewSet

router = SimpleRouter()
router.register("salas", SalaViewSet, basename="sala")

urlpatterns = router.urls
