from rest_framework.routers import DefaultRouter

from guests.views import GuestEntryViewSet, GuestListViewSet

router = DefaultRouter()
router.register("listas-invitados", GuestListViewSet, basename="listas-invitados")
router.register("invitados", GuestEntryViewSet, basename="invitados")

urlpatterns = router.urls
