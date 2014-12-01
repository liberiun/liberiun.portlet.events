from Acquisition import aq_inner
from DateTime import DateTime
from Products.CMFCore.utils import getToolByName
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from plone.app.layout.navigation.root import getNavigationRootObject
from plone.app.portlets import PloneMessageFactory as _
from plone.app.portlets.portlets import base
from plone.app.uuid.utils import uuidToObject
from plone.app.vocabularies.catalog import SearchableTextSourceBinder
from plone.memoize.compress import xhtml_compress
from plone.memoize.instance import memoize
from plone.portlets.interfaces import IPortletDataProvider
from zExceptions import NotFound
from zope import schema
from zope.component import getMultiAdapter
from zope.formlib import form
from zope.interface import implements


class IEventsPortlet(IPortletDataProvider):

    count = schema.Int(
        title=_(u'Number of items to display'),
        description=_(u'How many items to list.'),
        required=True,
        default=5
    )

    state = schema.Tuple(
        title=_(u"Workflow state"),
        description=_(u"Items in which workflow state to show."),
        default=None,
        required=False,
        value_type=schema.Choice(
            vocabulary="plone.app.vocabularies.WorkflowStates"
        )
    )

    search_base_uid = schema.Choice(
            title=_(u"portlet_label_search_base", default=u"Search base"),
            description=_(
                u'portlet_help_search_base',
                default=u'Select search base folder to search for events. This '
                    u'folder will also be used to link to in calendar '
                    u'searches. If empty, the whole site will be searched and '
                    u'the event listing view will be called on the site root.'),
            required=False,
            source=SearchableTextSourceBinder({'is_folderish': True},
                                              default_query='path:'))

class Assignment(base.Assignment):
    implements(IEventsPortlet)

    # reduce upgrade pain
    search_base = None

    def __init__(self, count=5, state=None, search_base_uid=None):
        self.count = count
        self.state = state
        self.search_base_uid = search_base_uid

    @property
    def title(self):
        return _(u"Liberiun Events")


class Renderer(base.Renderer):

    _template = ViewPageTemplateFile('portlet_events.pt')

    def __init__(self, *args):
        base.Renderer.__init__(self, *args)

        portal_state = getMultiAdapter((self.context, self.request), name=u'plone_portal_state')
        self.navigation_root_url = portal_state.navigation_root_url()
        self.portal = portal_state.portal()
        self.navigation_root_path = portal_state.navigation_root_path()
        self.navigation_root_object = getNavigationRootObject(self.context, self.portal)

    def render(self):
        return xhtml_compress(self._template())

    @property
    def available(self):
        return len(self._data())

    def get_location(self, event):
        return get_location(event)

    def events(self):
        return self._data()

    @memoize
    def have_events_folder(self):
        return 'events' in self.navigation_root_object.objectIds()

    def all_events_link(self):
        navigation_root_url = self.navigation_root_url
        search_base_path = self.search_base_path()

        if search_base_path:
            return search_base_path
        else:
            if self.have_events_folder():
                return '%s/events' % navigation_root_url
            else:
                return '%s/events_listing' % navigation_root_url

    def get_UID(self, path):
        portal = getToolByName(self, 'portal_url').getPortalObject()
        try:
            search_base = portal.unrestrictedTraverse(path.lstrip('/'))
        except (AttributeError, KeyError, TypeError, NotFound):
            return
        return search_base.UID()

    def search_base_path(self):
        uid = self.get_UID(self.data.search_base_uid)
        search_base = uuidToObject(uid)
        if search_base is not None:
            search_base = '/'.join(search_base.getPhysicalPath())
        return search_base

    @memoize
    def _data(self):
        context = aq_inner(self.context)
        catalog = getToolByName(context, 'portal_catalog')

        search_base_path = self.search_base_path()
        if search_base_path:
            path = {'query': search_base_path}
        else:
            path = self.navigation_root_path
        limit = self.data.count
        state = self.data.state
        if not state:
            state = ['published']

        return catalog(portal_type='Event',
                       review_state=state,
                       end={'query': DateTime(),
                            'range': 'min'},
                       path=path,
                       sort_on='start',
                       sort_limit=limit)[:limit]


class AddForm(base.AddForm):
    form_fields = form.Fields(IEventsPortlet)
    def create(self, data):
        return Assignment(**data)

class EditForm(base.EditForm):
    form_fields = form.Fields(IEventsPortlet)
    label = _(u"Add Liberiun Events Portlet")
    description = _(u"This portlet lists upcoming Events.")