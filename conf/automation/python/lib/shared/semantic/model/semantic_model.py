from openhab import logger, Registry

import java
import json
import re
import io
import locale


#https://github.com/openhab/openhab-core/blob/master/bundles/org.openhab.core.semantics/model/SemanticTags.csv
    
class SemanticItem:
    def __init__(self,item,semantic_type,semantic_properties,tags,synonyms,answer):
        self.item = item
        self.semantic_type = semantic_type
        self.semantic_properties = semantic_properties
        self.label = [item.getLabel().lower()] if item.getLabel() is not None else []
        self.tags = tags
        self.synonyms = synonyms
        self.answer = answer
        self.search_terms = list(set(self.label + self.synonyms + self.tags))

        self.children = []
        self.parents = []
        
    def getItem(self):
        return self.item

    def getSemanticType(self):
        return self.semantic_type

    def getSemanticProperties(self):
        return self.semantic_properties

    def getSearchTerms(self):
        return self.search_terms

    def getAnswer(self):
        return self.answer

    def getChildren(self):
        return self.children
      
    def getParents(self):
        return self.parents

    def __repr__(self):
        return self.item.getName() + " (" + str(self.label) + "|" + str(self.tags) + "|" + str(self.synonyms) + ")"

class SemanticModel:
    def test(self):
        #log.info("{}".format(self.semantic_items["pOther_Scene4"].answer))
        pass
      
    def __init__(self,item_registry,config):
        semantic_tags = {}
        
        # maybe it's possible to get the tags from bundle https://github.com/openhab/openhab-core/tree/main/bundles/org.openhab.core.semantics/src/main/resources
        # but ignore the first (the comment) line when parse file content bellow
        tag_file = "/openhab/conf/automation/python/lib/shared/semantic/config/tags.txt"
        language = locale.getlocale()[0].split("_")[0]
        if language != "en":
            tag_file = "/openhab/conf/automation/python/lib/shared/semantic/config/tags_" + language +".txt"
        f = io.open(tag_file, "r", encoding="utf-8")
        lines = f.readlines()
        for line in lines:
            keys,synonyms = line.strip().split("=")
            keys = keys.split("_")
            synonyms = synonyms.lower().split(",")
            type = keys[0]
            name = keys[-1]
            
            semantic_tags[name] = [type,synonyms]

        semantic_tags["Location"] = ["Location",[]]
        semantic_tags["Equipment"] = ["Equipment",[]]
        semantic_tags["Point"] = ["Point",[]]
        semantic_tags["Property"] = ["Property",[]]

        # build semantic items
        self.semantic_items = {}
        for item in item_registry.getItems():
            semantic_type = "Group" if item.getType() == "Group" else "Item"
            semantic_properties = []
            tags_search = []
            item_tags = item.getTags()
            for item_tag in item_tags:
                if item_tag in semantic_tags:
                    _semantic_type,_tags_search = semantic_tags[item_tag]
                    tags_search += _tags_search
                    if _semantic_type in ["Location","Equipment","Point"]:
                        semantic_type = _semantic_type
                    elif _semantic_type == "Property":
                        semantic_properties.append(item_tag)
                  
            #[u'semantics', u'synonyms']
            synonyms = Registry.getItemMetadata(item.getName(), "synonyms")
            synonym_search = synonyms.getValue().lower().split(",") if synonyms is not None else []
            synonym_search = list(map(str.strip, synonym_search))
            
            answer = Registry.getItemMetadata(item.getName(), "answer")
            answer = answer.getValue() if answer is not None else None

            semantic_item = SemanticItem(item,semantic_type,semantic_properties,tags_search,synonym_search,answer)
            self.semantic_items[semantic_item.item.getName()] = semantic_item

        # prepare semantic locations and children
        self.root_locations = []
        for semantic_item in self.semantic_items.values():
            if semantic_item.item.getType() == "Group":
                children = semantic_item.item.getMembers()
                #logger.info("-------------")
                #logger.info(semantic_item.item.getName())
                for item in children:
                    #logger.info(item.getName())
                    semantic_item.children.append(self.semantic_items[item.getName()])

                if semantic_item.getSemanticType() == "Location":
                    if len(semantic_item.item.getGroupNames()) == 0:
                        self.root_locations.append(semantic_item)
                        
        # prepare parents
        for semantic_item in self.semantic_items.values():
            for semantic_children in semantic_item.children:
                semantic_children.parents.append(semantic_item)

        # prepare regex matcher
        self.semantic_search_part_regex = {}
        self.semantic_search_full_regex = {}
        for semantic_item in self.semantic_items.values():
            for search_term in semantic_item.search_terms:
                if search_term in self.semantic_search_part_regex:
                    continue
                self.semantic_search_part_regex[search_term] = re.compile(config["main"]["phrase_part_matcher"].format(search_term))
                self.semantic_search_full_regex[search_term] = re.compile(config["main"]["phrase_full_matcher"].format(search_term))
                
                
    def getSemanticItem(self,item_name):
        return self.semantic_items[item_name]
    
    def getSearchFullRegex(self,search_term):
        return self.semantic_search_full_regex[search_term]
      
    def getSearchPartRegex(self,search_term):
        return self.semantic_search_part_regex[search_term]
      
    def getRootLocations(self):
        return self.root_locations
