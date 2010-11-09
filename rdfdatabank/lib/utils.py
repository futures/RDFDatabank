from datetime import datetime, timedelta

from redis import Redis
import simplejson

from pylons import app_globals as ag

from rdfobject.constructs import Manifest

from uuid import uuid4

import re

ID_PATTERN = re.compile(r"^[0-9A-z\-\:]+$")

def authz(granary_list,ident):
    g = ag.granary
    g.state.revert()
    g._register_silos()
    granary_list = g.silos
    def _parse_owners(silo_name):
        kw = g.describe_silo(silo_name)
        if "owners" in kw.keys():
            owners = [x.strip() for x in kw['owners'].split(",") if x]
            return owners
        else:
            return []
    
    if ident['role'] == "admin":
        return granary_list
    else:
        authd = []
        for item in granary_list:
            owners = _parse_owners(item)
            if ident['repoze.who.userid'] in owners:
                authd.append(item)
        return authd

def allowable_id(identifier):
    if ID_PATTERN.match(identifier):
        return identifier

def is_embargoed(silo, id, refresh=False):
    # TODO evaluate r.expire settings for these keys - popularity resets ttl or increases it?
    r = Redis()
    e = r.get("%s:%s:embargoed" % (silo.state['storage_dir'], id))
    e_d = r.get("%s:%s:embargoed_until" % (silo.state['storage_dir'], id))
    if refresh or (not e or not e_d):
        if silo.exists(id):
            item = silo.get_item(id)
            e = item.metadata.get("embargoed")
            e_d = item.metadata.get("embargoed_until")
            if e not in ['false', 0, False]:
                e = True
            else:
                e = False
            r.set("%s:%s:embargoed" % (silo.state['storage_dir'], id), e)
            r.set("%s:%s:embargoed_until" % (silo.state['storage_dir'], id), e_d)
    return (e, e_d)

def create_new(silo, id, creator, title=None, embargoed=True, embargoed_until=None, embargo_days_from_now=None, **kw):
    item = silo.get_item(id)
    item.metadata['createdby'] = creator
    item.metadata['embargoed'] = embargoed
    item.metadata['uuid'] = uuid4().hex
    item.add_namespace('oxds', "http://vocab.ox.ac.uk/dataset/schema#")
    item.add_triple(item.uri, u"rdf:type", "oxds:DataSet")

    if embargoed:
        if embargoed_until:
            embargoed_until_date = embargoed_until
        elif embargo_days_from_now:
            embargoed_until_date = (datetime.now() + timedelta(days=embargo_days_from_now)).isoformat()
        else:
            embargoed_until_date = (datetime.now() + timedelta(days=365*70)).isoformat()
        item.metadata['embargoed_until'] = embargoed_until_date
        item.add_triple(item.uri, u"oxds:isEmbargoed", 'True')
        item.add_triple(item.uri, u"oxds:embargoedUntil", embargoed_until_date)
    else:
        item.add_triple(item.uri, u"oxds:isEmbargoed", 'False')
    item.add_triple(item.uri, u"dcterms:identifier", id)
    item.add_triple(item.uri, u"dcterms:creator", creator)   
    item.add_triple(item.uri, u"dcterms:created", datetime.now())
    item.add_triple(item.uri, u"oxds:currentVersion", item.currentversion)
    
    #TODO: Add current version metadata
    if title:
        item.add_triple(item.uri, u"rdfs:label", title)
    item.sync()
    return item

def get_readme_text(item, filename="README"):
    with item.get_stream(filename) as fn:
        text = fn.read().decode("utf-8")
    return u"%s\n\n%s" % (filename, text)

def test_rdf(text):
    try:
        mani = Manifest()
        mani.from_string(text)
        return True
    except:
        return False
        
def munge_manifest(manifest_str, item, manifest_type='http://vocab.ox.ac.uk/dataset/schema#Grouping'):    
    #Get triples from the manifest file and remove the file
    triples = None
    ns = None
    ns, triples = read_manifest(item.uri, manifest_str, manifest_type=manifest_type)
    #item.add_namespace('owl', "http://www.w3.org/2002/07/owl#")
    if ns and triples:
        for k, v in ns.iteritems():
            item.add_namespace(k, v)
        for (s, p, o) in triples:
            if str(p) == 'http://purl.org/dc/terms/title':
                item.del_triple(item.uri, u"dcterms:title")    
            item.add_triple(s, p, o)
    item.sync()
    return True

def read_manifest(target_dataset_uri, manifest_str, manifest_type='http://vocab.ox.ac.uk/dataset/schema#Grouping'):
    triples = []
    namespaces = {}
    mani = Manifest()
    mani.from_string(manifest_str)    
    namespaces = mani.namespaces   
    for s_uri in mani.items_rdfobjects:
        datasetType = False
        #print '------------------ types ---------------------'
        #print mani.items_rdfobjects[s_uri].types
        #print '----------------  triples --------------------'
        #print mani.items_rdfobjects[s_uri].list_triples()
        #print '----------------------------------------------'
        for t in mani.items_rdfobjects[s_uri].types:
            if str(t) == manifest_type:
                datasetType = True
        if datasetType:
            #Add to existing uri and add a sameAs triple with this uri
            for s,p,o in mani.items_rdfobjects[s_uri].list_triples():
                triples.append((target_dataset_uri, p, o))
            namespaces['owl'] = "http://www.w3.org/2002/07/owl#"
            triples.append((target_dataset_uri, 'owl:sameAs', s_uri))
        else:
            for s,p,o in mani.items_rdfobjects[s_uri].list_triples():
                triples.append((s, p, o))
    return namespaces, triples

def manifest_type(manifest_str):
    mani_types = []
    mani = Manifest()
    mani.from_string(manifest_str)    
    for s_uri in mani.items_rdfobjects:
        for t in mani.items_rdfobjects[s_uri].types:
            mani_types.append(str(t))
    if "http://vocab.ox.ac.uk/dataset/schema#DataSet" in mani_types:
        return "http://vocab.ox.ac.uk/dataset/schema#DataSet"
    elif "http://vocab.ox.ac.uk/dataset/schema#Grouping" in mani_types:
        return "http://vocab.ox.ac.uk/dataset/schema#Grouping"
    return None

def serialisable_stat(stat):
    stat_values = {}
    for f in ['st_atime', 'st_blksize', 'st_blocks', 'st_ctime', 'st_dev', 'st_gid', 'st_ino', 'st_mode', 'st_mtime', 'st_nlink', 'st_rdev', 'st_size', 'st_uid']:
        try:
            stat_values[f] = stat.__getattribute__(f)
        except AttributeError:
            pass
    return stat_values
