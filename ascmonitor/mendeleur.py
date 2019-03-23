""" Access the Mendeley Database """

from typing import NamedTuple

import requests
from mendeley import Mendeley


class MendeleyAuthInfo(NamedTuple):
    """ Authentication infos for Mendeley """

    client_id: str
    client_secret: str
    redirect_uri: str
    user: str
    password: str


class Mendeleur:
    """ Manages Mendeley session """

    def __init__(self, authinfo, group_id):
        """ Authenticate the Mendeley client """
        mendeley = Mendeley(
            client_id=authinfo.client_id,
            client_secret=authinfo.client_secret,
            redirect_uri=authinfo.redirect_uri,
        )
        auth = mendeley.start_authorization_code_flow()
        login_url = auth.get_login_url()

        response = requests.post(
            login_url,
            allow_redirects=False,
            data={'username': authinfo.user, 'password': authinfo.password},
        )
        redirect_url = response.headers['Location']
        redirect_url = redirect_url.replace('http://', 'https://')

        self.session = auth.authenticate(redirect_url)
        self.group = self.session.groups.get(group_id)

    def all_documents(self):
        """
        Fetch the current library from mendeley.
        :returns: List of dicts with document bibliography
        """
        library = self.group.documents.iter(sort='created', order='desc', view='all')
        return list(self.transform_documents(doc for doc in library))

    def get_download_url(self, document_id):
        """ Return mendeley download url for a given document id """
        try:
            files = self.session.documents.get(document_id).files
            first_file = next(files.iter())
        except StopIteration:
            raise ValueError('Document has no file attached')
        return first_file.download_url

    def extract_disciplines(self, document):
        """ Extract disciplines from document tags """
        disciplines = []
        if document.tags:
            for tag in document.tags:
                if tag.lower().startswith('disc:'):
                    disciplines.extend(tag[5:].split(':'))
            document.json['disciplines'] = disciplines
        return document

    def fix_file_attached(self, document):
        """ Test file_attached attribute """
        if document.file_attached:
            document.json['file_attached'] = bool(list(document.files.iter()))
        return document

    def transform_documents(self, documents):
        """ Generator that transforms mendeley documents """
        for document in documents:
            document = self.extract_disciplines(document)
            document = self.fix_file_attached(document)
            yield document.json