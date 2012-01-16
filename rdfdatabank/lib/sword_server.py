from sss import SwordServer, Authenticator, Auth, ServiceDocument, SDCollection

from pylons import app_globals as ag

class SwordDataBank(SwordServer):
    """
    The main SWORD Server class.  This class deals with all the CRUD requests as provided by the web.py HTTP
    handlers
    """
    def __init__(self, config, auth):
        # get the configuration
        self.config = config
        self.auth_credentials = auth
        
        self.um = URLManager(config)

    def container_exists(self, path):
        raise NotImplementedError()

    def media_resource_exists(self, path):
        raise NotImplementedError()

    def service_document(self, path=None):
        """
        Construct the Service Document.  This takes the set of collections that are in the store, and places them in
        an Atom Service document as the individual entries
        """
        service = ServiceDocument(version=self.config.sword_version,
                                    max_upload_size=self.config.max_upload_size)
        
        # FIXME: at the moment, there is not authentication, so this is the
        # full list of silos
        
        # now for each collection create an sdcollection
        collections = []
        for col_name in ag.granary.silos:
            href = self.um.silo_url(col_name)
            title = col_name
            mediation = self.config.mediation
            
            # content types accepted
            accept = []
            multipart_accept = []
            if not self.config.accept_nothing:
                if self.config.app_accept is not None:
                    for acc in self.config.app_accept:
                        accept.append(acc)
                
                if self.config.multipart_accept is not None:
                    for acc in self.config.multipart_accept:
                        multipart_accept.append(acc)
                        
            # SWORD packaging formats accepted
            accept_package = []
            for format in self.config.sword_accept_package:
                accept_package.append(format)
            
            col = SDCollection(href=href, title=title, accept=accept, multipart_accept=multipart_accept,
                                accept_package=accept_package, mediation=mediation)
                                
            collections.append(col)
        
        service.add_workspace("Silos", collections)

        # serialise and return
        return service.serialise()
        
        """
        This is our reference for the service document - a list of silos appropriate to the user
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
            #For auth, the code is looking at the list of owners against each silo and not looking at the owner list against each user. A '*' here is meaningless.
            #TODO: Modify code to look at both and keep both silo owner and silos a user has acces to in users.py in sunc and use both
            if ident['role'] == "admin":
                authd = []
                for item in granary_list:
                    owners = _parse_owners(item)
                    if '*' in owners:
                        return granary_list
                    if ident['repoze.who.userid'] in owners:
                        authd.append(item)
                return authd
            else:
                authd = []
                for item in granary_list:
                    owners = _parse_owners(item)
                    if ident['repoze.who.userid'] in owners:
                        authd.append(item)
                return authd
        """

    def list_collection(self, path):
        """
        List the contents of a collection identified by the supplied id
        """
        raise NotImplementedError()

    def deposit_new(self, path, deposit):
        """
        Take the supplied deposit and treat it as a new container with content to be created in the specified collection
        Args:
        -collection:    the ID of the collection to be deposited into
        -deposit:       the DepositRequest object to be processed
        Returns a DepositResponse object which will contain the Deposit Receipt or a SWORD Error
        """
        raise NotImplementedError()

    def get_media_resource(self, path, accept_parameters):
        """
        Get a representation of the media resource for the given id as represented by the specified content type
        -id:    The ID of the object in the store
        -content_type   A ContentType object describing the type of the object to be retrieved
        """
        raise NotImplementedError()
    
    def replace(self, path, deposit):
        """
        Replace all the content represented by the supplied id with the supplied deposit
        Args:
        - oid:  the object ID in the store
        - deposit:  a DepositRequest object
        Return a DepositResponse containing the Deposit Receipt or a SWORD Error
        """
        raise NotImplementedError()

    def delete_content(self, path, delete):
        """
        Delete all of the content from the object identified by the supplied id.  the parameters of the delete
        request must also be supplied
        - oid:  The ID of the object to delete the contents of
        - delete:   The DeleteRequest object
        Return a DeleteResponse containing the Deposit Receipt or the SWORD Error
        """
        raise NotImplementedError()
        
    def add_content(self, path, deposit):
        """
        Take the supplied deposit and treat it as a new container with content to be created in the specified collection
        Args:
        -collection:    the ID of the collection to be deposited into
        -deposit:       the DepositRequest object to be processed
        Returns a DepositResponse object which will contain the Deposit Receipt or a SWORD Error
        """
        raise NotImplementedError()

    def get_container(self, path, accept_parameters):
        """
        Get a representation of the container in the requested content type
        Args:
        -oid:   The ID of the object in the store
        -content_type   A ContentType object describing the required format
        Returns a representation of the container in the appropriate format
        """
        raise NotImplementedError()

    def deposit_existing(self, path, deposit):
        """
        Deposit the incoming content into an existing object as identified by the supplied identifier
        Args:
        -oid:   The ID of the object we are depositing into
        -deposit:   The DepositRequest object
        Returns a DepositResponse containing the Deposit Receipt or a SWORD Error
        """
        raise NotImplementedError()

    def delete_container(self, path, delete):
        """
        Delete the entire object in the store
        Args:
        -oid:   The ID of the object in the store
        -delete:    The DeleteRequest object
        Return a DeleteResponse object with may contain a SWORD Error document or nothing at all
        """
        raise NotImplementedError()

    def get_statement(self, path):
        raise NotImplementedError()

    # NOT PART OF STANDARD, BUT USEFUL    
    # These are used by the webpy interface to provide easy access to certain
    # resources.  Not implementing them is fine.  If they are not implemented
    # then you just have to make sure that your file paths don't rely on the
    # Part http handler
        
    def get_part(self, path):
        """
        Get a file handle to the part identified by the supplied path
        - path:     The URI part which is the path to the file
        """
        raise NotImplementedError()
        
    def get_edit_uri(self, path):
        raise NotImplementedError()
    
class DataBankAuthenticator(Authenticator):
    def __init__(self, config): 
        self.config = config
        
    def basic_authenticate(self, username, password, obo):
        # FIXME: we're going to implement a very weak authentication mechanism
        # for the time being
        return Auth(username, obo)
        
class URLManager(object):
    def __init__(self, config):
        self.config = config
        
    def silo_url(self, silo):
        return self.config.base_url + silo
