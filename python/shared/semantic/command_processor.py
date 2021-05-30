# -*- coding: utf-8 -*-
import re

from shared.helper import  sendCommandIfChanged, getItemState

from config.semantic_config import SemanticConfig

from model.semantic_model import SemanticModel

class VoiceAction:
    def __init__(self,cmd):
        self.complete_search = cmd
        self.unprocessed_search = cmd
        
        self.location_matches = []
        
        self.points = []
        self.point_search_terms = []

        self.cmd = None
        self.cmd_search_terms = []
        
        self.item_actions = []
  
class ItemCommand:
    def __init__(self,cmd_config,cmd_type,cmd_value):
        self.cmd_config = cmd_config
        self.cmd_type = cmd_type
        self.cmd_value = cmd_value

class ItemAction:
    def __init__(self,item,cmd_type,cmd_value):
        self.item = item
        self.cmd_type = cmd_type
        self.cmd_value = cmd_value

class ItemMatcher:
    def __init__(self,semantic_item,full_match,part_match):
        self.semantic_item = semantic_item
        self.full_match = []
        for match in full_match:
            self.full_match += match.split(" ")
        #self.part_match = part_match
        self.part_match = []
        for match in part_match:
            self.part_match += match.split(" ")
        self.all_matches = set(self.full_match + self.part_match)
    
    def getPriority(self):
        return len(self.full_match) * 1.2 + len(self.part_match) * 1.1
        #return len(" ".join(self.full_match)) * 1.2 + len(" ".join(self.part_match)) * 1.1
 
class CommandProcessor:
    def __init__(self,log,ir):
        self.debug = False

        self.log = log
        
        self.semantic_model = SemanticModel(ir,SemanticConfig)
        self.semantic_model.test(self.log)
        
        self.full_phrase_map, self.full_phrase_terms = self.buildSearchMap(self.semantic_model.getSemanticItem(SemanticConfig["main"]["phrase_equipment"]).getChildren())
 
    def buildSearchMap(self,semantic_items):
        search_map = {}
        for semantic_item in semantic_items:
            for search_term in semantic_item.getSearchTerms():
                if search_term not in search_map:
                    search_map[search_term] = []
                search_map[search_term].append(semantic_item)
        search_terms = sorted(search_map, key=len, reverse=True)
        return search_map, search_terms
   
    def getItemsByType(self,parent,type):
        result = []
        if parent.getItem().getType() == "Group":
            #self.log.info(u" => {} {}".format(parent.getName(),parent.getType()))
            semantic_items = parent.getChildren()
            for semantic_item in semantic_items:
                #self.log.info(u" => {}".format(item.getName()))
                if semantic_item.getSemanticType() == type:
                    result.append(semantic_item)
                else:
                    result = result + self.getItemsByType(semantic_item,type)
        return result

    def _searchItems(self,semantic_item,unprocessed_search,items_to_skip,location_search,_full_matched_terms,_part_matched_terms,_processed_items):

        matches = []

        if semantic_item in items_to_skip or semantic_item in _processed_items:
            return matches

        _processed_items.append(semantic_item)

        new_matched_terms = []
        full_matched_terms = _full_matched_terms[:]
        part_matched_terms = _part_matched_terms[:]
  
        # check for matches
        is_match = False
        for search_term in semantic_item.getSearchTerms():
            if self.semantic_model.getSearchFullRegex(search_term).match(unprocessed_search):
                full_matched_terms.append(search_term)
                new_matched_terms.append(search_term)
                is_match = True
            elif self.semantic_model.getSearchPartRegex(search_term).match(unprocessed_search):
                part_matched_terms.append(search_term)
                new_matched_terms.append(search_term)
                is_match = True

        # check if matches are just sub phrases
        # => phrases which never works alone
        total_matched_terms = full_matched_terms + part_matched_terms
        if  len(total_matched_terms) == 1 and total_matched_terms[0] in SemanticConfig["main"]["phrase_sub"]:
            full_matched_terms = part_matched_terms = total_matched_terms = new_matched_terms = []
            is_match = False

        if location_search:
            # clean unprocessed search terms    
            for search_term in new_matched_terms:
                unprocessed_search = unprocessed_search.replace(search_term,"")

        # check sub elements
        if semantic_item.getItem().getType() == "Group":
            for _item in semantic_item.getItem().getMembers():
                try:
                    _semantic_item = self.semantic_model.getSemanticItem(_item.getName())
                    if location_search and _semantic_item.getSemanticType() != semantic_item.getSemanticType():
                        continue
                    matches += self._searchItems(_semantic_item,unprocessed_search,items_to_skip,location_search,full_matched_terms,part_matched_terms,_processed_items)
                except KeyError:
                    #self.log.info(u"item {} not found".format(_item.getName()))
                    pass
                
        # add own match only if there are no sub matches
        if is_match and len(matches) == 0:
            matches.append(ItemMatcher(semantic_item,list(set(full_matched_terms)),list(set(part_matched_terms))))
    
        return matches
         
    def detectLocations(self,actions):
        for action in actions:
            matches = []
            for semantic_location in self.semantic_model.getRootLocations():
                matches += self._searchItems(semantic_location,action.unprocessed_search,items_to_skip=[],location_search=True,_full_matched_terms=[],_part_matched_terms=[],_processed_items=[])
            action.location_matches = matches

    def fillLocationsFallbacks(self,actions,fallback_location_name):
        # Fill missing locations forward
        last_matches = []
        for action in actions:
            # if no location found use the last one
            if len(action.location_matches) == 0:
                action.location_matches = last_matches
            else:
                last_matches = action.location_matches
 
        # Fill missing locations backward
        last_matches = []
        for action in reversed(actions):
            if len(action.location_matches) == 0:
                action.location_matches = last_matches
            else:
                last_matches = action.location_matches

        # Fill missing locations with fallbacks
        if fallback_location_name != None:
            for action in actions:
                if len(action.location_matches) != 0:
                    continue
                action.location_matches = [ ItemMatcher(self.semantic_model.getSemanticItem(fallback_location_name),[],[]) ]
    
    def checkPoints(self,action,unprocessed_search,items_to_skip):
        results = {}
        
        for location_match in action.location_matches:
          
            _unprocessed_search = unprocessed_search
            for matched_search in location_match.all_matches:
                _unprocessed_search = _unprocessed_search.replace(matched_search,"")
                
            if self.debug:
                self.log.info(u"  location: '{}' => '{}'".format(location_match.semantic_item.getItem().getName(),location_match.all_matches))
            
            equipments = self.getItemsByType(location_match.semantic_item,"Equipment")
            for equipment in equipments:

                matches = self._searchItems(equipment,_unprocessed_search,items_to_skip=items_to_skip,location_search=False,_full_matched_terms=[],_part_matched_terms=[],_processed_items=[])
                for match in matches:
                    if self.debug:
                        self.log.info(u"      item: '{}' => '{}'".format(match.semantic_item.getItem().getName(),match.all_matches))

                    key = u"{},{}".format(u",".join(location_match.all_matches),u",".join(match.all_matches))
                    if key not in results:
                        results[key] = [location_match.getPriority() + match.getPriority(),match.all_matches, []]

                    if match.semantic_item.getSemanticType() == "Equipment":
                        results[key][2] += self.getItemsByType(match.semantic_item,"Point")
                    else:
                        results[key][2].append(match.semantic_item)
                    
        # check which result combination (location/equipment/property) has the highest priority
        final_priority = 0
        final_key = None
        action.points = []
        action.point_search_terms = []
        for key in results:
            match = results[key]
            #self.log.info(u"{} {}".format(key,match))
            
            if match[0] < final_priority:
                continue
            
            if match[0] == final_priority:
                if key != final_key:
                    if len(key) <= len(final_key):
                        continue
                else:
                    action.points += match[2]
                    continue

            final_key = key
            final_priority = match[0]
            action.point_search_terms = match[1]
            action.points = match[2]
                
        if final_key is not None:
            for search in final_key.split(","):
                unprocessed_search = unprocessed_search.replace(search,"")
        
        action.unprocessed_search = unprocessed_search
 
    def detectPoints(self,actions):
        for action in actions:
            # search for points based on voice_cmd
            self.checkPoints(action,action.unprocessed_search,[])

    def fillPointFallbacks(self,actions):
        # Fill missing points backward until command is found
        last_action = None
        for action in reversed(actions):
            if action.cmd != None: # maybe not needed
                last_action = None
 
            if len(action.points) == 0:
                if last_action != None:
                    self.checkPoints(action,u"{} {}".format(" ".join(last_action.point_search_terms),action.unprocessed_search),last_action.points)
            else:
                last_action = action
 
        # Fill missing points forwards
        last_action = None
        for action in actions:
            # if no points where found search again based on the last cmd with points
            if len(action.points) == 0:
                if last_action != None:
                    self.checkPoints(action,u"{} {}".format(" ".join(last_action.point_search_terms),action.unprocessed_search),last_action.points)
            else:
                last_action = action

    def prepareCommandValue(self,cmd_type,value):
        if cmd_type in SemanticConfig["mappings"]:
            if value in SemanticConfig["mappings"][cmd_type]:
                value = SemanticConfig["mappings"][cmd_type][value]
            if cmd_type == "PERCENT": 
                if not value.isnumeric():
                    value = None
        return value
          
    def checkCommand(self,action):
        # check if we have a unique property like Light or ColorTemperature
        main_properties = []
        for point in action.points:
            main_properties += point.semantic_properties
        main_property = main_properties[0] if len(set(main_properties)) == 1 else None

        # if no main_property detected
        # 1. we use the first cmd which matches search => later in validareActions, we filter out all points which are not supported by this command
        # 2. if we have a main property, we use the first cmd where search and tags matches

        #self.log.info(u">>>> {}".format(main_property))

        for cmd_type in SemanticConfig["commands"]:
            for cmd_config in SemanticConfig["commands"][cmd_type]:
                for search in cmd_config["search"]:
                    #self.log.info(u"{} {}".format(cmd_type,search))
                    if cmd_config["value"] == "REGEX":
                        #self.log.info(u"{} {}".format(search[1:-1],action.unprocessed_search))
                        match = re.match(SemanticConfig["main"]["phrase_full_matcher"].format(search),action.unprocessed_search)
                        if match and (main_property is None or main_property in cmd_config["tags"]):
                            value = match.group(2)
                            value = self.prepareCommandValue(cmd_type,value)
                            if value is not None:
                                return cmd_type,cmd_config,value
                    else:
                        parts = action.unprocessed_search.split(" ")
                        if search in parts:
                            action.cmd_search_terms.append(search)
                            return cmd_type, cmd_config, cmd_config["value"]
        return None, None, None
                                
    def detectCommand(self,actions):
        for action in actions:
            # search for cmd based on voice_cmd
            cmd_type, cmd_config, cmd_value = self.checkCommand(action)
            if cmd_type is not None:
                action.cmd = ItemCommand(cmd_config,cmd_type,cmd_value)
 
    def fillCommandFallbacks(self,actions):
        # Fill missing commands backward
        last_action = None
        for action in reversed(actions):
            if action.cmd is None:
                if last_action != None:
                    action.cmd = last_action.cmd
            else:
                last_action = action

        # Fill missing commands forward
        last_action = None
        for action in actions:
            # if no cmd found use the last one
            if action.cmd is None:
                if last_action != None:
                    action.cmd = last_action.cmd
            else:
                last_action = action

    def validateActions(self,actions):
        processed_items = {}
        for action in actions:
            for point in action.points:
                item_name = point.item.getName()
                #self.log.info(u"{}".format(item_name))
                if item_name in processed_items \
                    or action.cmd is None \
                    or ( "types" in action.cmd.cmd_config and point.item.getType() not in action.cmd.cmd_config["types"] ) \
                    or ( "tags" in action.cmd.cmd_config and len(filter(lambda x: x in action.cmd.cmd_config["tags"], point.item.getTags()))==0  ):
                    # TODO debug if all cases makes sence
                    #self.log.info(u">>>>skip {} {}".format(item_name,action.cmd))
                    continue
                processed_items[item_name] = True
                action.item_actions.append(ItemAction(point.item,action.cmd.cmd_type,action.cmd.cmd_value))
        #self.log.info(u"{}".format(processed_items.keys()))
              
    def process(self,voice_command, fallback_location_name):
        actions = []
        voice_command = voice_command.lower()

        # check for full text phrases
        for search in self.full_phrase_terms:
            if search == voice_command:
                action = VoiceAction(search)
                for semantic_item in self.full_phrase_map[search]:
                    action.item_actions.append(ItemAction(semantic_item.getItem(),"SWITCH","ON"))
                actions.append(action)
                #self.log.info(u"{}".format(search))
                break
     
        # check for item commands
        if len(actions)==0:
            for read_phrase in SemanticConfig["commands"]["READ"][0]["synonyms"]:
                if re.match( SemanticConfig["main"]["phrase_full_matcher"].format(read_phrase), voice_command):
                    voice_command = voice_command.replace(read_phrase,SemanticConfig["commands"]["READ"][0]["synonyms"][read_phrase])

            sub_voice_commands = voice_command.split(SemanticConfig["main"]["phrase_separator"])
            for sub_voice_command in sub_voice_commands:
                actions.append(VoiceAction(sub_voice_command))

            self.detectLocations(actions)
            self.fillLocationsFallbacks(actions,fallback_location_name)

            self.detectPoints(actions)

            self.detectCommand(actions)

            self.fillPointFallbacks(actions) # depends on detected commands

            self.fillCommandFallbacks(actions)

            self.validateActions(actions)
 
        return actions
 
    def getFormattedValue(self,item):
        value = getItemState(item).toString()
        if item.getType() == "Dimmer":
            if value == "0":
                value = SemanticConfig["states"]["OFF"]
            elif value == "100":
                value = SemanticConfig["states"]["ON"]
            else:
                value = u"{} %".format(value)
        elif item.getType() == "Rollershutter":
            if value == "0":
                value = SemanticConfig["states"]["UP"]
            elif value == "100":
                value = SemanticConfig["states"]["DOWN"]
            else:
                value = u"{} %".format(value)
        if value in SemanticConfig["states"]:
            value = SemanticConfig["states"][value]
        return value

    def getParentByType(self,semantic_item,type):
        for parent in semantic_item.getParents():
            if parent.getSemanticType() == "Group":
                continue
            if parent.getSemanticType() == type:
                return parent
            return self.getParentByType(parent,type)

    def getAnswer(self,semantic_item):
        semantic_equipment = self.getParentByType(semantic_item,"Equipment")
        semantic_location = self.getParentByType(semantic_equipment,"Location")
        #semantic_location = self.getParentByType(semantic_item,"Location")
 
        value = self.getFormattedValue(semantic_item.getItem())
        
        for tag in semantic_item.getItem().getTags():
            if tag not in SemanticConfig["answers"]:
                continue
            return SemanticConfig["answers"][tag].format(room=semantic_location.getItem().getLabel(),state=value)

        semantic_reference = semantic_equipment if len(semantic_equipment.getChildren()) == 1 else semantic_item

        return SemanticConfig["answers"]["Default"].format(equipment=semantic_reference.getItem().getLabel(),room=semantic_location.getItem().getLabel(),state=value)

    def applyActions(self,actions,voice_command,dry_run):
        missing_locations = []
        missing_points = []
        missing_cmds = []
        unsupported_cmds = []
        for action in actions:
            if len(action.item_actions) > 0:
                continue

            if len(action.location_matches) == 0:
                missing_locations.append(action.unprocessed_search)
            elif len(action.points) == 0:
                missing_points.append(action.unprocessed_search)
            elif action.cmd is None:
                missing_cmds.append(action.unprocessed_search)
            else:
                unsupported_cmds.append(action.unprocessed_search)

        is_valid = False
        join_separator = SemanticConfig["i18n"]["message_join_separator"]
        if len(actions) == len(missing_locations):
            msg = SemanticConfig["i18n"]["nothing_found"].format(term=voice_command)
        elif len(missing_locations) > 0:
            msg = SemanticConfig["i18n"]["nothing_found"].format(term=join_separator.join(missing_locations))
        elif len(missing_points) > 0:
            msg = SemanticConfig["i18n"]["no_equipment_found_in_phrase"].format(term=join_separator.join(missing_points))
        elif len(missing_cmds) > 0:
            msg = SemanticConfig["i18n"]["no_cmd_found_in_phrase"].format(term=join_separator.join(missing_cmds))
        elif len(unsupported_cmds) > 0:
            msg = SemanticConfig["i18n"]["no_supported_cmd_in_phrase"].format(term=join_separator.join(unsupported_cmds))
        else:
            msg = SemanticConfig["i18n"]["ok_message"]
            is_valid = True

        if is_valid:
            msg_r = []
            for action in actions:
                for item_action in action.item_actions:
                    semantic_item = self.semantic_model.getSemanticItem(item_action.item.getName())
                    if item_action.cmd_type == "READ":
                        msg_r.append(self.getAnswer(semantic_item))
                        #answer_data.append([item_action.item,value])
                    else:
                        if not dry_run:
                            sendCommandIfChanged(item_action.item,item_action.cmd_value)

                        if semantic_item.getAnswer() is not None:
                            msg_r.append(semantic_item.getAnswer()) 
            if len(msg_r) > 0:
                if len(msg_r) > 2:
                    msg_r = [ msg_r[0], SemanticConfig["i18n"]["more_results"].format(count=len(msg_r)-1) ]

                msg = SemanticConfig["i18n"]["message_join_separator"].join(msg_r)
 
        return msg, is_valid
      
    def parseData(self,input):
        data = input.split("|")
        for replace in SemanticConfig["main"]["replacements"]:
            data[0] = data[0].replace(replace[0],replace[1])
        if len(data) == 1:
            return [ data[0], None ]
        else:
            client_id = data[1].replace("amzn1.ask.device.","")
            return [ data[0], client_id ]
