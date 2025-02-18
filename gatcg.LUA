
function setDecklist(player, value)
  ui_decklist_state[player.color] = value
end


function spawnDeck(name, cards, player, as_bag)
  playmat = getObjectFromGUID(playmats[player.color])
  rotation = playmat.getRotation()
  position = playmat.positionToWorld(deck_position[name])
  bounds = playmat.getBounds()
  sleeve = getSleeves(player)
  deck = getDeck(name, cards, player)
  if as_bag then
    deck = getDeckBag(name, deck)
  end
  deck.Transform.posX = position.x
  deck.Transform.posY = playmat.getPosition().y + bounds.size.y + bounds.offset.y + 1
  deck.Transform.posZ = position.z
  deck.Transform.rotY = rotation.y
  return spawnObjectData({data = deck})
end

print("abd")

function getDeckBag(name, deck)
  return {
    Name = "Infinite_Bag",
    Transform = {
      scaleX = 1,
      scaleY = 1,
      scaleZ = 1,
      rotX = 0,
      rotY = 0,
      rotZ = 0
    },
    Nickname = name,
    ContainedObjects = {deck}
  }
end

function getDeck(name, cards, player)
  sleeve = getSleeves(player)
  deck_ids = {}
  custom_deck = {}
  contained_objects = {}
  index = 1
  for _, card in ipairs(cards) do
    for i=1, card.quantity do
      custom_card = getCustomCard(card.image, sleeve)
      deck_ids[index] = (index + 100) * 100
      custom_deck[index + 100] = custom_card
      contained_objects[index] = getCard(custom_card, card.name, index)
      index = index + 1
    end
  end
  if #contained_objects == 1 then
    deck = contained_objects[1]
    deck.Transform.rotZ = 180
    return deck
  else
    return {
      Name = "Deck",
      Transform = {
        rotX = 0,
        rotY = 0,
        rotZ = 180,
        scaleX = card_scale,
        scaleY = 1,
        scaleZ = card_scale
      },
      Nickname = name,
      DeckIDs = deck_ids,
      CustomDeck = custom_deck,
      ContainedObjects = contained_objects
    }
  end
end


function getCustomCard(image, sleeve)
  return {
    FaceURL = image,
    BackURL = sleeve,
    NumWidth = 1,
    NumHeight = 1,
    BackIsHidden = true,
    UniqueBack = false,
    Type = 0
  }
end

function getCard(custom_card, name, index)
  card_index = index + 100
  return {
    Name = "CardCustom",
    Transform = {
      scaleX = card_scale,
      scaleY = 1,
      scaleZ = card_scale
    },
    Nickname = name,
    CardID = card_index * 100,
    CustomDeck = {
      [card_index] = custom_card
    }
  }
end

-- Import
function importDeck(player, value, index)
  deck_url = ui_decklist_state[player.color]
  sleeve = ui_sleeve_state[player.color]
  if sleeve == nil or sleeve == "" then
    sleeve = card_back
  end

  if deck_url ~= nil and deck_url:len() > 0 then
    if deck_url:sub(1, 5) ~= "https" then
      deck_url = "https://" .. deck_url
    end
    -- Silvie
    if deck_url:find("silvie.org") ~= nil then
        if deck_url:find("format=json") == nil then
            if deck_url:find("?") == nil then
              deck_url = deck_url .. "?format=json"
            else
              deck_url = deck_url .. "&format=json"
            end
        end
    -- ShoutAtYourDecks
    elseif deck_url:find("shoutatyourdecks.com") ~= nil then
      deck_url = deck_url:gsub("/decks/", "/api/")
    else
      broadcastToColor("Invalid Decklist URL!", player.color, {255,0,0})
      return
    end

    WebRequest.get(deck_url, function(req)
      if req.is_error then
        log(request.error)
      else
        json = JSON.decode(req.text)
        if json.error ~= nil then
          log(json.error)
          if json.error == "silvie/bad-request" then
            broadcastToColor("Invalid Silvie.org Decklist!", player.color, {255,0,0})
          else
            broadcastToColor("Unknown Error :(", player.color, {255,0,0})
          end
        else
          -- Generate Cards
          for deck, cards in pairs(json.cards) do
            if #cards > 0 then
              spawnDeck(deck, cards, player, index=="import_deck_bag")
            end
          end
        end
      end
    end)
  end
end

--[[
 Grand Archive TCG PvE
 PvE Mod created by Lee
 Based on Mod created by Chris Orrell, Edited by Leo
 Grand Archive created by weebs of the Shore LLC, all rights reserved.

 GA Website : https://www.gatcg.com/
 Grand Archive Discord : https://discord.gg/grandarchivetcg
--]]

-- Constants
card_scale = 1.42055011
img_host = "https://img.silvie.org/api-data/"
card_back = "https://img.silvie.org/cdn/deck-builder/card-back.png"
list_tokens_url = "https://api.gatcg.com/cards/search?type=TOKEN&page_size=50"

-- Object References
playmats = {
  Red = "35894d",
  Blue = "f0607e",
  Green = "53ddd0",
  Purple = "a251c2",
  Brown = "3f5c70"
}
ui_decklist_state = {}
ui_sleeve_state = {}
tokens = {}

-- Snappoints
local left_col0_x_off = 1.92
local left_col_x_off = 1.385
local left_col2_x_off = 1.05
local right_col0_x_off = -left_col0_x_off
local right_col_x_off = -left_col_x_off
local right_col2_x_off = -left_col2_x_off

local left_mid_col_x_off = 0.425
local right_mid_col_x_off = -left_mid_col_x_off

local top_row_z_off = -0.638
local middle_row_z_off = -0.07
local bottom_row_z_off = 0.58

local memory_row_z = 0.7

deck_position = {
  material = {left_col_x_off, 0, middle_row_z_off},
  main = {right_col_x_off, 0, middle_row_z_off},
  sideboard = {left_col_x_off, 0, top_row_z_off},
  token = {0, 0, top_row_z_off},
  generated = {0, 0, middle_row_z_off},
  spawn = {right_col0_x_off, 0, middle_row_z_off}
}

function setMatSnapPoints(mat)
  snap_points = {
    -- Banished
    { position = {right_col_x_off,0,top_row_z_off},
      rotation = {0,90,0},
      rotation_snap = true },
    -- Main Deck Zone
    { position = deck_position["main"],
      rotation = {0,0,0},
      rotation_snap = true },
    -- Graveyard
    { position = {right_col_x_off,0,bottom_row_z_off},
      rotation = {0,0,0},
      rotation_snap = true },

    -- Memory 1
    { position = {-0.875,0,memory_row_z},
      rotation = {0,0,0},
      rotation_snap = true },
    -- Memory 2
    { position = {-0.700,0,memory_row_z},
      rotation = {0,0,0},
      rotation_snap = true },
    -- Memory 3
    { position = {-0.525,0,memory_row_z},
      rotation = {0,0,0},
      rotation_snap = true },
    -- Memory 4
    { position = {-0.350,0,memory_row_z},
      rotation = {0,0,0},
      rotation_snap = true },
    -- Memory 5
    { position = {-0.175,0,memory_row_z},
      rotation = {0,0,0},
      rotation_snap = true },
    -- Memory 6
    { position = {0.0,0,memory_row_z},
      rotation = {0,0,0},
      rotation_snap = true },
    -- Memory 7
    { position = {0.175,0,memory_row_z},
      rotation = {0,0,0},
      rotation_snap = true },
   -- Memory 8
    { position = {0.350,0,memory_row_z},
      rotation = {0,0,0},
      rotation_snap = true },
    -- Memory 9
    { position = {0.525,0,memory_row_z},
      rotation = {0,0,0},
      rotation_snap = true },
   -- Memory 10
    { position = {0.700,0,memory_row_z},
      rotation = {0,0,0},
      rotation_snap = true },
    -- Memory 11
    { position = {0.875,0,memory_row_z},
      rotation = {0,0,0},
      rotation_snap = true },
  }
  if mat.getVar("color") ~= "Brown" then
    -- Mat. Deck
    snap_points[#snap_points + 1] = {
      position = deck_position["material"],
      rotation = {0,0,0},
      rotation_snap = true
    }
  end
  mat.setSnapPoints(snap_points)

  mat.interactable = false
end

-- UI
function toggleImportLayout(player)
  toggleVisibility(player, "import_layout")
  toggleVisibility(player, "menu_layout")
end

function toggleTokenLayout(player)
  if #tokens == 0 then
    getTokens()
  end
  toggleVisibility(player, "token_layout")
  toggleVisibility(player, "menu_layout")
end

function toggleVisibility(player, id)
  visibility = Global.UI.getAttribute(id, "visibility")
  visible = visibility:find(player.color) ~= nil
  if visible then
    Global.UI.setAttribute(id, "visibility", visibility:gsub("|" .. player.color, ""))
  else
    Global.UI.setAttribute(id, "visibility", visibility .. "|" .. player.color)
  end
end

function setSleeve(player, value)
  ui_sleeve_state[player.color] = value
end

function setDecklist(player, value)
  ui_decklist_state[player.color] = value
end

-- Decks/Cards
function getSleeves(player)
  sleeve = ui_sleeve_state[player.color]
  if sleeve == nil or sleeve == "" then
    sleeve = card_back
  end
  return sleeve
end

function spawnDeck(name, cards, player, as_bag)
  playmat = getObjectFromGUID(playmats[player.color])
  rotation = playmat.getRotation()
  position = playmat.positionToWorld(deck_position[name])
  bounds = playmat.getBounds()
  sleeve = getSleeves(player)
  deck = getDeck(name, cards, player)
  if as_bag then
    deck = getDeckBag(name, deck)
  end
  deck.Transform.posX = position.x
  deck.Transform.posY = playmat.getPosition().y + bounds.size.y + bounds.offset.y + 1
  deck.Transform.posZ = position.z
  deck.Transform.rotY = rotation.y
  return spawnObjectData({data = deck})
end

function spawnToken(player, value, id)
  playmat = getObjectFromGUID(playmats[player.color])
  position = playmat.positionToWorld(deck_position["spawn"])
  bounds = playmat.getBounds()
  index = tonumber(id:gsub("token", ""), 10)
  token = tokens[index]
  custom_token = getCustomCard(token.url, getSleeves(player))
  card = getCard(custom_token, token.name, index)
  card.Transform.posX = position.x
  card.Transform.posY = playmat.getPosition().y + bounds.size.y + bounds.offset.y + 1
  card.Transform.posZ = position.z
  card.Transform.rotX = 0
  card.Transform.rotY = playmat.getRotation().y
  card.Transform.rotZ = 0
  spawnObjectData({data = card})
end

function getDeckBag(name, deck)
  return {
    Name = "Infinite_Bag",
    Transform = {
      scaleX = 1,
      scaleY = 1,
      scaleZ = 1,
      rotX = 0,
      rotY = 0,
      rotZ = 0
    },
    Nickname = name,
    ContainedObjects = {deck}
  }
end

global_offset = 0

function getDeck(name, cards, player)
  local sleeve = getSleeves(player)

  local deck_ids = {}
  local custom_deck = {}
  local contained_objects = {}

  global_offset = (global_offset % 30) + 1
  local deckOffset = global_offset * 1000

  local index = 1
  for _, card in ipairs(cards) do
    for i = 1, card.quantity do
      local custom_card = getCustomCard(card.image, sleeve)
      local customIndex = deckOffset + (index + 100)
      deck_ids[index] = customIndex * 100
      custom_deck[customIndex] = custom_card
      contained_objects[index] = getCard(custom_card, card.name, deckOffset + index)
      index = index + 1
    end
  end

  if #contained_objects == 1 then
    local single = contained_objects[1]
    single.Transform.rotZ = 180
    return single
  else
    return {
      Name = "Deck",
      Transform = {
        rotX = 0,
        rotY = 0,
        rotZ = 180,
        scaleX = card_scale,
        scaleY = 1,
        scaleZ = card_scale
      },
      Nickname = name,
      DeckIDs = deck_ids,
      CustomDeck = custom_deck,
      ContainedObjects = contained_objects
    }
  end
end


function getCustomCard(image, sleeve)
  return {
    FaceURL = image,
    BackURL = sleeve,
    NumWidth = 1,
    NumHeight = 1,
    BackIsHidden = true,
    UniqueBack = false,
    Type = 0
  }
end

function getCard(custom_card, name, index)
  -- index might already include deckOffset
  local card_index = (index + 100) * 100
  return {
    Name = "CardCustom",
    Transform = {
      scaleX = card_scale,
      scaleY = 1,
      scaleZ = card_scale
    },
    Nickname = name,
    CardID = card_index,
    CustomDeck = {
      [index + 100] = custom_card
    }
  }
end

-- Import
function importDeck(player, value, index)
  deck_url = ui_decklist_state[player.color]
  sleeve = ui_sleeve_state[player.color]
  if sleeve == nil or sleeve == "" then
    sleeve = card_back
  end

  if deck_url ~= nil and deck_url:len() > 0 then
    if deck_url:sub(1, 5) ~= "https" then
      deck_url = "https://" .. deck_url
    end
    -- Silvie
    if deck_url:find("silvie.org") ~= nil then
        if deck_url:find("format=json") == nil then
            if deck_url:find("?") == nil then
              deck_url = deck_url .. "?format=json"
            else
              deck_url = deck_url .. "&format=json"
            end
        end
    -- ShoutAtYourDecks
    elseif deck_url:find("shoutatyourdecks.com") ~= nil then
      deck_url = deck_url:gsub("/decks/", "/api/")
    else
      broadcastToColor("Invalid Decklist URL!", player.color, {255,0,0})
      return
    end

    WebRequest.get(deck_url, function(req)
      if req.is_error then
        log(request.error)
      else
        json = JSON.decode(req.text)
        if json.error ~= nil then
          log(json.error)
          if json.error == "silvie/bad-request" then
            broadcastToColor("Invalid Silvie.org Decklist!", player.color, {255,0,0})
          else
            broadcastToColor("Unknown Error :(", player.color, {255,0,0})
          end
        else
          -- Generate Cards
          for deck, cards in pairs(json.cards) do
            if #cards > 0 then
              spawnDeck(deck, cards, player, index=="import_deck_bag")
            end
          end
        end
      end
    end)
  end
end

-- Tokens
list_generated_card1_url = "https://api.gatcg.com/cards/search?name=creeping torment&page_size=1"
list_generated_card2_url = "https://api.gatcg.com/cards/search?name=cosmic bolt&page_size=1"
list_tokens_url         = "https://api.gatcg.com/cards/search?type=TOKEN&page_size=50"

-- This holds the final combined tokens from all requests
tokens = {}

function getTokens()
    if #tokens > 0 then return end
    local combinedTokens = {}
    local outstanding = 3

    local function handleResponse(req)
        if req.is_error then
            log(req.error)
            return
        end
        local jsonData = JSON.decode(req.text)
        for _, token in ipairs(jsonData.data) do
            table.insert(combinedTokens, {
                name = token.name,
                url  = img_host .. token.result_editions[1].uuid .. ".jpg"
            })
        end
    end

    local function checkDone()
        outstanding = outstanding - 1
        if outstanding == 0 then
            tokens = combinedTokens

            local ui = Global.UI.getXmlTable()
            local token_buttons = {}
            local token_assets = {}
            for index, token in ipairs(tokens) do
                table.insert(token_buttons, {
                    tag = "Button",
                    attributes = {
                        id      = "token" .. index,
                        icon    = "token" .. index,
                        onClick = "spawnToken"
                    }
                })
                table.insert(token_assets, {
                    name = "token" .. index,
                    url  = token.url
                })
            end

            Global.UI.setCustomAssets(token_assets)
            ui[1].children[3].children[1].children[1].children = token_buttons
            Global.UI.setXmlTable(ui, token_assets)
        end
    end

    WebRequest.get(list_tokens_url, function(req)
        handleResponse(req)
        checkDone()
    end)

    WebRequest.get(list_generated_card1_url, function(req)
        handleResponse(req)
        checkDone()
    end)

    WebRequest.get(list_generated_card2_url, function(req)
        handleResponse(req)
        checkDone()
    end)
end
