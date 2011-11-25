from datetime import datetime
import json     #FIXME: fallback to simplejson if json not available

from django.http import HttpResponse, Http404
from django.views.generic import View


class BackboneView(View):
    """
    Abstract class view, which makes it easy for subclasses to talk to backbone.js.

    Supported operations (copied from backbone.js docs):
        create -> POST   /collection
        read ->   GET    /collection[/id]
        update -> PUT    /collection/id
        delete -> DELETE /collection/id
    """
    base_queryset = None        # Queryset to use for all data accesses, eg. User.objects.all()
    add_form_class = None       # Form class to be used for POST requests
    edit_form_class = None      # Form class to be used for PUT requests
    serialize_fields = tuple()  # Tuple of field names that should appear in json output

    def get(self, request, *args, **kwargs):
        """
        Handle GET requests, either for a single resource or a collection.
        """
        if kwargs.get('id'):
            return self.get_single_item(request, *args, **kwargs)
        else:
            return self.get_collection(request, *args, **kwargs)

    def get_single_item(self, request, *args, **kwargs):
        """
        Handle a GET request for a single model instance.
        """
        try:
            qs = self.base_queryset.filter(id=kwargs['id'])
            assert len(qs) == 1
        except AssertionError:
            raise Http404
        output = self.serialize_qs(qs)
        return self.build_response(output)

    def get_collection(self, request, *args, **kwargs):
        """
        Handle a GET request for a full collection (when no id was provided).
        """
        qs = self.base_queryset
        output = self.serialize_qs(qs)
        return self.build_response(output)

    def post(self, request, *args, **kwargs):
        """
        Handle a POST request by adding a new model instance.

        This view will only do something if BackboneView.add_form_class is specified
        by the subclass. This should be a ModelForm corresponding to the model used by
        base_queryset.

        Backbone.js will send the new object's attributes as json in the request body,
        so use json.loads() to parse it, rather than looking at request.POST.
        """
        if self.add_form_class != None:
            try:
                request_dict = json.loads(request.raw_post_data)
            except ValueError:
                return HttpResponse('Invalid POST JSON', status=400)
            form = self.add_form_class(request_dict)
            if form.is_valid():
                new_object = form.save()
            return HttpResponse('OK')   #FIXME: send json of new model
        else:
            return HttpResponse('POST not supported', status=405)

    def put(self, request, *args, **kwargs):
        pass

    def delete(self, request, *args, **kwargs):
        pass

    def serialize_qs(self, queryset):
        """
        Serialize a queryset into a JSON object that can be consumed by backbone.js.
        """
        values = queryset.values(*self.serialize_fields)
        if self.kwargs.get('id'):
            # For single-item requests, convert ValuesQueryset to a dict simply
            # by slicing the first item:
            json_output = json.dumps(values[0], default=BackboneView.date_serializer)
        else:
            json_output = json.dumps(list(values), default=BackboneView.date_serializer)
        return json_output

    def build_response(self, output):
        """
        Convert json output to an HttpResponse object, with the correct mimetype.
        """
        return HttpResponse(output, mimetype='application/json')

    @staticmethod
    def date_serializer(obj):
        """
        Convert datetime objects to ISO-compatible strings during json serialization.
        """
        return obj.isoformat() if isinstance(obj, datetime.datetime) else None
