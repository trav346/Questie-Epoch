---@class QuestieEventHandler
local QuestieEventHandler = QuestieLoader:CreateModule("QuestieEventHandler")
local _EventHandler = QuestieEventHandler.private

-------------------------
-- Import modules
-------------------------
---@type QuestieQuest
local QuestieQuest = QuestieLoader:ImportModule("QuestieQuest")
---@type QuestieJourney
local QuestieJourney = QuestieLoader:ImportModule("QuestieJourney")
---@type QuestieComms
local QuestieComms = QuestieLoader:ImportModule("QuestieComms")
---@type QuestieProfessions
local QuestieProfessions = QuestieLoader:ImportModule("QuestieProfessions")
---@type QuestieTracker
local QuestieTracker = QuestieLoader:ImportModule("QuestieTracker")
---@type TrackerBaseFrame
local TrackerBaseFrame = QuestieLoader:ImportModule("TrackerBaseFrame")
---@type TrackerQuestFrame
local TrackerQuestFrame = QuestieLoader:ImportModule("TrackerQuestFrame")
---@type TrackerUtils
local TrackerUtils = QuestieLoader:ImportModule("TrackerUtils")
---@type QuestieReputation
local QuestieReputation = QuestieLoader:ImportModule("QuestieReputation")
---@type QuestieNameplate
local QuestieNameplate = QuestieLoader:ImportModule("QuestieNameplate")
---@type QuestieMap
local QuestieMap = QuestieLoader:ImportModule("QuestieMap")
---@type QuestiePlayer
local QuestiePlayer = QuestieLoader:ImportModule("QuestiePlayer")
---@type QuestieAuto
local QuestieAuto = QuestieLoader:ImportModule("QuestieAuto")
---@type QuestieAnnounce
local QuestieAnnounce = QuestieLoader:ImportModule("QuestieAnnounce")
---@type QuestieCombatQueue
local QuestieCombatQueue = QuestieLoader:ImportModule("QuestieCombatQueue")
---@type QuestieInit
local QuestieInit = QuestieLoader:ImportModule("QuestieInit")
---@type MinimapIcon
local MinimapIcon = QuestieLoader:ImportModule("MinimapIcon")
---@type QuestgiverFrame
local QuestgiverFrame = QuestieLoader:ImportModule("QuestgiverFrame")
---@type QuestieDebugOffer
local QuestieDebugOffer = QuestieLoader:ImportModule("QuestieDebugOffer")
---@type AvailableQuests
local AvailableQuests = QuestieLoader:ImportModule("AvailableQuests")

--- COMPATIBILITY ---
local C_Timer = QuestieCompat.C_Timer
local UnitInParty = QuestieCompat.UnitInParty

local questAcceptedMessage = string.gsub(ERR_QUEST_ACCEPTED_S, "(%%s)", "(.+)")
local questCompletedMessage = string.gsub(ERR_QUEST_COMPLETE_S, "(%%s)", "(.+)")

local FACTION_STANDING_CHANGED_PATTERN

--======================
-- Event Registration
--======================

function QuestieEventHandler:RegisterEarlyEvents()
    Questie:RegisterEvent("PLAYER_LOGIN", function(...) _EventHandler:PlayerLogin(...) end)
end

function QuestieEventHandler:RegisterLateEvents()
    -- Level / Combat
    Questie:RegisterEvent("PLAYER_LEVEL_UP", function(...) _EventHandler:PlayerLevelUp(...) end)
    Questie:RegisterEvent("PLAYER_REGEN_DISABLED", function(...) _EventHandler:PlayerRegenDisabled(...) end)
    Questie:RegisterEvent("PLAYER_REGEN_ENABLED", function(...) _EventHandler:PlayerRegenEnabled(...) end)

    -- Map / Tooltip
    Questie:RegisterEvent("MAP_EXPLORATION_UPDATED", function(...) _EventHandler:MapExplorationUpdated(...) end)
    Questie:RegisterEvent("MODIFIER_STATE_CHANGED", function(...) _EventHandler:ModifierStateChanged(...) end)
    Questie:RegisterEvent("PLAYER_ALIVE", function(...)
        QuestieTracker:UpdateDurabilityFrame()
        QuestieTracker:UpdateVoiceOverFrame()
    end)

    -- Professions / Reputations
    Questie:RegisterBucketEvent("CHAT_MSG_SKILL", 2, function(...) _EventHandler:ChatMsgSkill(...) end)
    Questie:RegisterBucketEvent("CHAT_MSG_COMBAT_FACTION_CHANGE", 2, function(...) _EventHandler:ChatMsgCompatFactionChange(...) end)
    Questie:RegisterEvent("CHAT_MSG_SYSTEM", function(...) _EventHandler:ChatMsgSystem(...) end)

    -- Spells
    Questie:RegisterEvent("NEW_RECIPE_LEARNED", function()
        AvailableQuests.CalculateAndDrawAll()
    end)

    -- Quest UI Events
    Questie:RegisterEvent("UI_INFO_MESSAGE", function(...) _EventHandler:UiInfoMessage(...) end)
    Questie:RegisterEvent("QUEST_FINISHED", QuestieAuto.QUEST_FINISHED)
    Questie:RegisterEvent("QUEST_ACCEPTED", QuestieAuto.QUEST_ACCEPTED)
    Questie:RegisterEvent("QUEST_DETAIL", function(...) 
        QuestieAuto.QUEST_DETAIL(...)
        if Questie.IsSoD then QuestieDebugOffer.QuestDialog(...) end
    end)
    Questie:RegisterEvent("QUEST_PROGRESS", QuestieAuto.QUEST_PROGRESS)
    Questie:RegisterEvent("GOSSIP_SHOW", function(...)
        QuestieAuto.GOSSIP_SHOW(...)
        QuestgiverFrame.GossipMark(...)
    end)
    Questie:RegisterEvent("QUEST_GREETING", function(...)
        QuestieAuto.QUEST_GREETING(...)
        QuestgiverFrame.GreetingMark(...)
    end)
    Questie:RegisterEvent("QUEST_ACCEPT_CONFIRM", QuestieAuto.QUEST_ACCEPT_CONFIRM)
    Questie:RegisterEvent("GOSSIP_CLOSED", QuestieAuto.GOSSIP_CLOSED)
    Questie:RegisterEvent("QUEST_COMPLETE", function(...)
        QuestieAuto.QUEST_COMPLETE(...)
        if Questie.IsSoD then QuestieDebugOffer.QuestDialog(...) end
        -- Fix the issue where the map icon does not disappear after completing the quests
        C_Timer.After(0.2, function()
            QuestieQuest:SmoothReset()
            QuestieMap:DrawAllAvailableQuestIcons()
            QuestieTracker:Update()
        end)
    end)

    -- Achievements
    if Questie.IsWotlk or QuestieCompat.Is335 then
        Questie:RegisterEvent("ACHIEVEMENT_EARNED", function(index, achieveId, alreadyEarned)
            QuestieTracker:UntrackAchieveId(achieveId)
            QuestieTracker:UpdateAchieveTrackerCache(achieveId)
            if (not AchievementFrame) then AchievementFrame_LoadUI() end
            AchievementFrameAchievements_ForceUpdate()
            QuestieCombatQueue:Queue(function() QuestieTracker:Update() end)
        end)
        Questie:RegisterEvent("TRACKED_ACHIEVEMENT_LIST_CHANGED", function(index, achieveId, added)
            QuestieTracker:UpdateAchieveTrackerCache(achieveId)
        end)
        Questie:RegisterEvent("TRACKED_ACHIEVEMENT_UPDATE", function(self, achieveId)
            QuestieCombatQueue:Queue(function()
                if QuestieCompat.Is335 then QuestieTracker:UpdateAchieveTrackerCache(achieveId) end
                QuestieTracker:Update()
            end)
        end)
    end

    -- Debug / Loot / Comms
    if Questie.IsSoD then Questie:RegisterEvent("LOOT_OPENED", QuestieDebugOffer.LootWindow) end
    Questie:RegisterBucketEvent("GROUP_ROSTER_UPDATE", 1, function(...) _EventHandler.GroupRosterUpdate(...) end)
    Questie:RegisterEvent("GROUP_JOINED", function(...) _EventHandler:GroupJoined(...) end)
    Questie:RegisterEvent("GROUP_LEFT", function(...) _EventHandler:GroupLeft(...) end)

    -- Nameplates
    Questie:RegisterEvent("NAME_PLATE_UNIT_ADDED", QuestieNameplate.NameplateCreated)
    Questie:RegisterEvent("NAME_PLATE_UNIT_REMOVED", QuestieNameplate.NameplateDestroyed)
    Questie:RegisterEvent("PLAYER_TARGET_CHANGED", QuestieNameplate.DrawTargetFrame)

    -- Loot announcements
    Questie:RegisterEvent("CHAT_MSG_LOOT", function(_, text, notPlayerName, _, _, playerName)
        if QuestieCompat.Is335 then playerName = QuestieCompat.ChatMessageLoot(text) end
        QuestieTracker.QuestItemLooted(_, text)
        QuestieAnnounce.ItemLooted(_, text, notPlayerName, _, _, playerName)
    end)

    -- World Enter
    Questie:RegisterEvent("PLAYER_ENTERING_WORLD", function()
        if Questie.started then
            QuestieMap:InitializeQueue()
            local isInInstance, instanceType = IsInInstance()
            local skipInstance = isInInstance and (instanceType == "raid" or instanceType == "pvp" or instanceType == "arena")
            if not skipInstance then QuestieQuest:SmoothReset() end
        end
    end)
end

--======================
-- Event Handlers
--======================

function _EventHandler:PlayerLogin()
    if not Questie.db or not QuestieConfig then
        Questie:Error("Config DB from saved variables not loaded!")
        error("Config DB from saved variables not loaded!")
        return
    end

    if WorldMapDetailFrame then
        hooksecurefunc(WorldMapDetailFrame, "SetScale", QuestieMap.RescaleIcons)
    end

    -- Faction pattern
    local locale = GetLocale()
    local FACTION_STANDING_CHANGED_LOCAL = FACTION_STANDING_CHANGED or "You are now %s with %s."
    local replaceString = ".+"
    local replaceTypes = {
        ruRU = "%(%%%d$s%)", zhTW = "%%s%(%%s%)", deDE = "%%%d$s", zhCNkoKR = "%%%d$s", enPlus = "%%s",
    }

    if locale == "zhCN" or locale == "koKR" then
        FACTION_STANDING_CHANGED_PATTERN = string.gsub(FACTION_STANDING_CHANGED_LOCAL, replaceTypes.zhCNkoKR, replaceString)
    elseif locale == "deDE" then
        FACTION_STANDING_CHANGED_PATTERN = string.gsub(FACTION_STANDING_CHANGED_LOCAL, replaceTypes.deDE, replaceString)
    elseif locale == "zhTW" then
        FACTION_STANDING_CHANGED_PATTERN = string.gsub(FACTION_STANDING_CHANGED_LOCAL, replaceTypes.zhTW, replaceString)
    elseif locale == "ruRU" then
        FACTION_STANDING_CHANGED_PATTERN = string.gsub(FACTION_STANDING_CHANGED_LOCAL, replaceTypes.ruRU, replaceString)
    else
        FACTION_STANDING_CHANGED_PATTERN = string.gsub(FACTION_STANDING_CHANGED_LOCAL, replaceTypes.enPlus, replaceString)
    end

    QuestieInit:Init()
end

function _EventHandler:ChatMsgSystem(message)
    if string.find(message, questCompletedMessage) == 1 or string.find(message, questAcceptedMessage) == 1 then
        MinimapIcon:UpdateText(message)
    elseif string.find(message, FACTION_STANDING_CHANGED_PATTERN) then
        QuestieReputation:Update()
    end
end

function _EventHandler:UiInfoMessage(errorType, message)
    local messages = {
        ["ERR_QUEST_OBJECTIVE_COMPLETE_S"] = true,
        ["ERR_QUEST_UNKNOWN_COMPLETE"] = true,
        ["ERR_QUEST_ADD_KILL_SII"] = true,
        ["ERR_QUEST_ADD_FOUND_SII"] = true,
        ["ERR_QUEST_ADD_ITEM_SII"] = true,
        ["ERR_QUEST_ADD_PLAYER_KILL_SII "] = true,
        ["ERR_QUEST_FAILED_S"] = true,
    }
    if messages[GetGameMessageInfo(errorType)] then
        MinimapIcon:UpdateText(message)
    end
end

function _EventHandler:MapExplorationUpdated()
    if Questie.db.profile.hideUnexploredMapIcons then
        QuestieMap.utils:MapExplorationUpdate()
    end
    if Questie.IsWotlk then
        QuestieCombatQueue:Queue(function() QuestieTracker:Update() end)
    end
end

function _EventHandler:PlayerLevelUp(level)
    QuestiePlayer:SetPlayerLevel(level)
    C_Timer.After(3, function()
        QuestiePlayer:SetPlayerLevel(level)
        AvailableQuests.CalculateAndDrawAll()
    end)
    QuestieJourney:PlayerLevelUp(level)
end

function _EventHandler:ModifierStateChanged(key, down)
    -- Keep the original Shift/Ctrl function
    if QuestieTracker.started then TrackerUtils:ShowVoiceOverPlayButtons() end
end

function _EventHandler:ChatMsgSkill()
    local isProfUpdate, isNewProfession = QuestieProfessions:Update()
    if isProfUpdate or isNewProfession then AvailableQuests.CalculateAndDrawAll() end
    if Questie.IsWotlk or QuestieCompat.Is335 then
        QuestieCombatQueue:Queue(function() QuestieTracker:Update() end)
    end
end

function _EventHandler:ChatMsgCompatFactionChange()
    local factionChanged, newFaction = QuestieReputation:Update(false)
    if factionChanged or newFaction then
        QuestieCombatQueue:Queue(function() QuestieTracker:Update() end)
        AvailableQuests.CalculateAndDrawAll()
    end
end

function _EventHandler.GroupRosterUpdate()
    local currentMembers = GetNumGroupMembers()
    QuestiePlayer.numberOfGroupMembers = currentMembers
end

function _EventHandler:GroupJoined()
    local checkTimer
    checkTimer = C_Timer.NewTicker(0.2, function()
        local partyPending = UnitInParty("player")
        local isInParty = UnitInParty("party1")
        local isInRaid = UnitInRaid("raid1")
        if partyPending and (isInParty or isInRaid) then
            Questie:SendMessage("QC_ID_REQUEST_FULL_QUESTLIST")
            checkTimer:Cancel()
        elseif not partyPending then
            checkTimer:Cancel()
        end
    end)
end

function _EventHandler:GroupLeft()
    QuestieComms:ResetAll()
end

local trackerHiddenByCombat, optionsHiddenByCombat, journeyHiddenByCombat = false, false, false
function _EventHandler:PlayerRegenDisabled()
    if QuestieTracker then
        if Questie.db.profile.hideTrackerInCombat and Questie.db.char.isTrackerExpanded and not trackerHiddenByCombat then
            trackerHiddenByCombat = true
            QuestieTracker:Collapse()
        end
        if IsInInstance() and Questie.db.profile.hideTrackerInDungeons then QuestieTracker:Collapse() end
    end
    if QuestieConfigFrame and QuestieConfigFrame:IsShown() then
        optionsHiddenByCombat = true
        QuestieConfigFrame:Hide()
    end
    if QuestieJourney and QuestieJourney:IsShown() then
        journeyHiddenByCombat = true
        QuestieJourney.ToggleJourneyWindow()
    end
end

function _EventHandler:PlayerRegenEnabled()
    if Questie.db.profile.hideTrackerInCombat and trackerHiddenByCombat then
        if (not Questie.db.profile.hideTrackerInDungeons) or (not IsInInstance()) then
            trackerHiddenByCombat = false
            QuestieTracker:Expand()
        end
        QuestieCombatQueue:Queue(function() QuestieTracker:Update() end)
    end
    if optionsHiddenByCombat then QuestieConfigFrame:Show() optionsHiddenByCombat = false end
    if journeyHiddenByCombat then QuestieJourney.ToggleJourneyWindow() journeyHiddenByCombat = false end
end

return _EventHandler
