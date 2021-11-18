from collective.collectionfilter.interfaces import IGroupByCriteria, IGroupByModifier
from collective.taxonomy import PATH_SEPARATOR, PRETTY_PATH_SEPARATOR, utility
from collective.taxonomy.interfaces import ITaxonomy
from plone import api
from plone.behavior.interfaces import IBehavior
from six.moves.urllib.parse import parse_qsl, urlparse
from zope.component import adapter
from zope.component.hooks import getSite
from zope.component import queryUtility
from zope.interface import implementer


def resolve_title(token, index_name):
    sm = getSite().getSiteManager()
    utilities = sm.getUtilitiesFor(ITaxonomy)
    taxonomies = [uname for uname, util in utilities]
    shortname = None
    taxonomy_name = None
    for tax in taxonomies:
        shortname = tax[len("collective.taxonomy.") :]
        if not index_name.endswith(shortname):
            continue
        taxonomy_name = tax
    if not shortname or not taxonomy_name:
        return token
    taxonomy = queryUtility(ITaxonomy, name=taxonomy_name)
    lang = api.portal.get_current_language()
    lang = lang in taxonomy.inverted_data and lang or taxonomy.default_language
    term = taxonomy.translate(token, target_language=lang)
    return term


def resolve_filter_order(filter_option):
    sm = getSite().getSiteManager()
    taxonomies = sm.getUtilitiesFor(ITaxonomy)
    filter_query_string = urlparse(filter_option["url"]).query
    filter_query = parse_qsl(filter_query_string)

    taxonomy_index_name = None

    for query_name, query_value in filter_query:
        if query_value == filter_option["value"]:
            if taxonomy_index_name:
                # Todo: How to handle multiple matching taxonomies?
                return None
            taxonomy_index_name = query_name

    if not taxonomy_index_name:
        # Todo: How to handle the case where the filter is not in the query
        return None

    filter_taxonomy = None

    for taxonomy_id, taxonomy in taxonomies:
        behavior_name = taxonomy.getGeneratedName()
        behavior = sm.queryUtility(IBehavior, name=behavior_name)
        if behavior.field_name == taxonomy_index_name:
            filter_taxonomy = taxonomy

    if not filter_taxonomy:
        # Todo: How to handle the case where no taxonomy is found
        return None

    # `getCurrentLanguage` taxes a `request` paramater but doesn't use it
    current_language = filter_taxonomy.getCurrentLanguage(None)
    items = [val for val in filter_taxonomy.order[current_language].values()]

    import pdb

    pdb.set_trace()


@implementer(IGroupByModifier)
@adapter(IGroupByCriteria)
def groupby_modifier(groupby):
    sm = getSite().getSiteManager()
    utilities = sm.getUtilitiesFor(ITaxonomy)
    for taxonomy in utilities:
        behavior = sm.queryUtility(IBehavior, name=taxonomy[1].getGeneratedName())
        taxonomy_field_prefix = behavior.field_prefix
        taxonomy_shortname = taxonomy[1].getShortName()
        taxonomy_index_name = "{0}{1}".format(taxonomy_field_prefix, taxonomy_shortname)
        groupby._groupby[taxonomy_index_name] = {
            "index": taxonomy_index_name,
            "metadata": taxonomy_index_name,
            "display_modifier": lambda it, idx: resolve_title(it, idx),
            "sort_key_function": resolve_filter_order,
        }
