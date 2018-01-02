from django.contrib import messages
from django.contrib.admin.utils import unquote
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import router
from django.db.models.deletion import Collector
from django.http import Http404, HttpResponseRedirect
from django.views import generic
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from material.viewset import viewprop

from .base import has_object_perm


class DeleteModelView(generic.DeleteView):
    viewset = None

    def has_delete_permission(self, request, obj=None):
        if self.viewset is not None:
            return self.viewset.has_delete_permission(request, obj=obj)
        else:
            return has_object_perm(request.user, 'delete', self.model, obj=obj)

    def get_deleted_objects(self):
        collector = Collector(using=router.db_for_write(self.object))
        collector.collect([self.object])
        return collector.data

    @viewprop
    def queryset(self):
        if self.viewset is not None and hasattr(self.viewset, 'get_queryset'):
            return self.viewset.get_queryset(self.request)
        return None

    def get_object(self):
        pk = self.kwargs.get(self.pk_url_kwarg)
        if pk is not None:
            pk = unquote(pk)
            try:
                self.kwargs[self.pk_url_kwarg] = self.model._meta.pk.to_python(pk)
            except (ValidationError, ValueError):
                raise Http404
        obj = super().get_object()

        if not self.has_delete_permission(self.request, obj):
            raise PermissionDenied

        return obj

    def get_template_names(self):
        """
        List of templates for the view.
        If no `self.template_name` defined, uses::
             [<app_label>/<model_label>_delete.html,
              'material/views/confirm_delete.html']
        """
        if self.template_name is None:
            opts = self.model._meta
            return [
                '{}/{}{}.html'.format(opts.app_label, opts.model_name, self.template_name_suffix),
                'material/views/confirm_delete.html',
            ]
        return [self.template_name]

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()

        # to be sure that str(self.object) works, prepare message before object deletion
        message = format_html(
            _("The {obj} was deleted successfully."),
            obj=str(self.object),
        )
        self.object.delete()
        messages.add_message(self.request, messages.SUCCESS, message, fail_silently=True)
        return HttpResponseRedirect(success_url)

    def get_success_url(self):
        if self.viewset and hasattr(self.viewset, 'get_success_url'):
            return self.viewset.get_success_url(self.request)
        return '../'