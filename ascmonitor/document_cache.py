"""
Stores the document library in a database
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Callable, Optional, Tuple

from pymongo.database import Database

from ascmonitor import DocumentType, DocumentsType

# TODO: if it becomes are problem, make sure slugs never change


@dataclass
class Changes:
    created: DocumentsType = field(default_factory=list)
    updated: DocumentsType = field(default_factory=list)
    removed: DocumentsType = field(default_factory=list)

    def items(self):
        """ Similar to dict.items """
        return asdict(self).items()


class DocumentCache:
    """ Provides access to stored document data. """

    collection_name = "documents"
    meta_collection_name = "documents_meta"

    def __init__(self, mongo: Database, source_fn: Callable[[], DocumentsType], expires: int):
        """
        :param mongo: mongo db instance
        :param source_fn: function that is called on cache miss
        :param expires: expiration time of cache in seconds
        """
        self._mongo = mongo
        self._collection = mongo[self.collection_name]
        self._meta = mongo[self.meta_collection_name]
        self._source_fn = source_fn
        self._expires = expires

        # init cache
        self._collection.create_index("slug")

    @property
    def expired(self):
        """ Returns True if cache has expired """
        now = datetime.now()
        meta_doc = self._meta.find_one()
        if meta_doc is None:
            return True
        return meta_doc["expiry"] > now

    def get(self) -> Tuple[DocumentsType, Changes]:
        """ Get the documents and list of changes """
        if not self.expired:
            documents = self._get_from_cache()
            changes = Changes()
        else:
            documents, changes = self._get_from_source()
        return documents, changes

    def get_by_slug(self, slug: str) -> Optional[DocumentType]:
        """ Return document by slug or None if not found """
        return self._collection.find_one({"slug": slug})

    def get_by_id(self, id_: str) -> Optional[DocumentType]:
        """ Return document by id_ or None if not found """
        return self._collection.find_one({"_id": id_})

    def update(self) -> Changes:
        """ Force update """
        _, changes = self._get_from_source()
        return changes

    def _get_from_cache(self) -> DocumentsType:
        """ Return from cache or None """
        data = list(self._collection.find())
        return data

    @staticmethod
    def _set_id_field(documents: DocumentsType, field_: str):
        """ Set custom id from field as mongo id """
        return [{"_id": d[field_], **d} for d in documents]

    @staticmethod
    def diff(old: DocumentsType, new: DocumentsType) -> Changes:
        """ Returns list of changes """
        old_docs = {d["id"]: d for d in old}
        new_docs = {d["id"]: d for d in new}

        old_ids = set(old_docs.keys())
        new_ids = set(new_docs.keys())
        created = [new_docs[id_] for id_ in new_ids - old_ids]
        removed = [old_docs[id_] for id_ in old_ids - new_ids]

        updated = []
        for id_ in old_ids & new_ids:
            if old_docs[id_] != new_docs[id_]:
                updated.append(new_docs[id_])

        return Changes(created=created, removed=removed, updated=updated)

    def _get_from_source(self) -> Tuple[DocumentsType, Changes]:
        """ Return from source and put in cache """
        documents = self._source_fn()
        changes = self.put(documents)
        return documents, changes

    def put(self, documents: DocumentsType) -> Changes:
        """
        Update documents in collection and set expiration.
        :returns: Differences between old and new documents
        """
        # make sure documents have correct id
        documents = self._set_id_field(documents, "id")

        # get old documents to build diff
        old = self._get_from_cache()

        # replace documents
        self._collection.delete_many({})
        self._collection.insert_many(documents)
        self._meta.insert_one({"expiry": datetime.now() + timedelta(seconds=self._expires)})

        # build and return diff
        new = self._get_from_cache()
        changes = self.diff(old, new)
        return changes
