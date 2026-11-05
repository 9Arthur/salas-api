from rest_framework.routers import SimpleRouter

from reservas.views import ReservaViewSet, SalaViewSet

router = SimpleRouter()
router.register("salas", SalaViewSet, basename="sala")
router.register("reservas", ReservaViewSet, basename="reserva")

urlpatterns = router.urls
