# Game resource table reference

Generated from the APK-derived schema and existing server data; see manifest.json for source hashes.
IDs are table-scoped; row order is retained. Client variants preserve capture values.

| ID | Wire table | Server JSON | Rows | Primary key | Separate client JSON |
| --- | --- | --- | --- | --- | --- |
| 1 | `consume` | `tables/items/consume.json` | 11 | i_id | no |
| 2 | `music` | `tables/music/music.json` | 50 | i_id | yes |
| 3 | `costume` | `tables/items/costumes.json` | 61 | i_id | yes |
| 4 | `prop` | `tables/items/props.json` | 17 | i_id | no |
| 5 | `follower` | `tables/followers/followers.json` | 23 | i_id | yes |
| 6 | `buff` | `tables/skills/buffs.json` | 5 | i_id | no |
| 7 | `unit` | `tables/characters/units.json` | 6 | i_id | yes |
| 8 | `skill` | `tables/skills/skills.json` | 8 | i_id | yes |
| 9 | `achievement` | `tables/quests/achievements.json` | 17 | i_id | no |
| 10 | `daily_mission` | `tables/quests/daily_missions.json` | 6 | i_id | yes |
| 11 | `music_level` | `tables/music/levels.json` | 50 | i_Level | yes |
| 12 | `shop` | `tables/shops/products.json` | 45 | i_id | yes |
| 13 | `reward_group` | `tables/rewards/groups.json` | 1289 | i_id | no |
| 14 | `Fan` | `tables/characters/fan_levels.json` | 12 | i_Area, i_Grade | no |
| 15 | `SystemNotification` | `tables/localization/notifications.json` | 49 | i_Id | no |
| 16 | `SystemString` | `tables/localization/strings.json` | 567 | i_StringID | no |
| 17 | `SubscribeList` | `tables/passes/seasons.json` | 13 | i_id | no |
| 18 | `SubscribePassReward` | `tables/passes/rewards.json` | 416 | i_id | no |
| 19 | `SubscribePass` | `tables/passes/rules.json` | 13 | i_id | no |
| 20 | `Guitar` | `tables/items/guitars.json` | 85 | i_id | yes |
| 21 | `SubscribePassRewardInformation` | `tables/passes/reward_information.json` | 78 | i_id | no |
| 22 | `ticketcollection` | `tables/items/tickets.json` | 26 | i_id | no |
| 23 | `character` | `tables/characters/characters.json` | 2 | i_id | yes |
| 24 | `samseckevent` | `tables/events/meowfest.json` | 3 | i_id | yes |
| 25 | `localpush` | `tables/localization/local_push.json` | 12 | i_id | no |
| 26 | `followerquest` | `tables/quests/follower_quests.json` | 68 | i_id | yes |
| 27 | `proplevel` | `tables/items/prop_levels.json` | 340 | i_id | yes |
| 28 | `follower_profile` | `tables/followers/profiles.json` | 22 | i_id | no |
| 29 | `passgoodsshop` | `tables/shops/pass_goods.json` | 13 | i_id | no |
| 30 | `followergiftitem` | `tables/items/follower_gifts.json` | 6 | i_id | no |
| 31 | `followerprofilelevel` | `tables/followers/profile_levels.json` | 440 | i_id | no |
| 32 | `ad_list` | `tables/ads/placements.json` | 2 | i_id | no |
| 33 | `chthird_stage` | `tables/chapters/stages.json` | 41 | i_id | no |
| 34 | `chthird_score` | `tables/chapters/scores.json` | 50 | i_id | no |
| 35 | `chthird_chapter` | `tables/chapters/chapters.json` | 2 | i_id | no |
| 36 | `percent` | `tables/rewards/drop_candidates.json` | 120 | i_id | no |
| 37 | `ad_level` | `tables/ads/levels.json` | 80 | i_id | no |
| 38 | `event_list` | `tables/events/schedule.json` | 5 | idx | no |
| 39 | `select_reward` | `tables/rewards/selection.json` | 12 | i_id | no |

## Field dictionary

Field names and types are schema facts, not inferred gameplay implementations.

### consume

| Thrift ID | Name | Type |
| --- | --- | --- |
| 1 | `i_id` | I32 |
| 2 | `s_ResourceName` | STRING |
| 3 | `s_Title_KO` | STRING |
| 4 | `s_Title_EN` | STRING |
| 5 | `s_Title_JA` | STRING |
| 6 | `s_Title_ZH_CHS` | STRING |
| 7 | `s_Title_ZH_CHT` | STRING |
| 8 | `s_Title_VI` | STRING |
| 9 | `s_Title_ES` | STRING |
| 10 | `s_Title_IT` | STRING |
| 11 | `s_Title_ID` | STRING |
| 12 | `s_Title_TH` | STRING |
| 13 | `s_Title_PT` | STRING |
| 14 | `s_Title_HI` | STRING |
| 15 | `s_Limit` | STRING |
| 16 | `i_Type` | I16 |
| 17 | `s_ExtraValue` | STRING |
| 18 | `i_Area` | I16 |
| 19 | `b_IsActive` | I16 |

### music

| Thrift ID | Name | Type |
| --- | --- | --- |
| 1 | `i_id` | I32 |
| 2 | `s_Title_KO` | STRING |
| 3 | `s_Title_EN` | STRING |
| 4 | `s_Title_JA` | STRING |
| 5 | `s_Title_ZH_CHS` | STRING |
| 6 | `s_Title_ZH_CHT` | STRING |
| 7 | `s_Title_VI` | STRING |
| 8 | `s_Title_ES` | STRING |
| 9 | `s_Title_IT` | STRING |
| 10 | `s_Title_ID` | STRING |
| 11 | `s_Title_TH` | STRING |
| 12 | `s_Title_PT` | STRING |
| 13 | `s_Title_HI` | STRING |
| 14 | `s_Description_1_KO` | STRING |
| 15 | `s_Description_1_EN` | STRING |
| 16 | `s_Description_1_JA` | STRING |
| 17 | `s_Description_1_ZH_CHS` | STRING |
| 18 | `s_Description_1_ZH_CHT` | STRING |
| 19 | `s_Description_1_VI` | STRING |
| 20 | `s_Description_1_ES` | STRING |
| 21 | `s_Description_1_IT` | STRING |
| 22 | `s_Description_1_ID` | STRING |
| 23 | `s_Description_1_TH` | STRING |
| 24 | `s_Description_1_PT` | STRING |
| 25 | `s_Description_1_HI` | STRING |
| 26 | `s_ResourceName` | STRING |
| 27 | `s_MusicFileName` | STRING |
| 28 | `i_MaxLevel` | I64 |
| 29 | `d_LevelRate` | DOUBLE |
| 30 | `d_LateCost` | I64 |
| 31 | `d_Cost` | DOUBLE |
| 32 | `d_CostIncreaseValue` | DOUBLE |
| 33 | `d_CostValueConstant` | I64 |
| 34 | `d_Amount` | DOUBLE |
| 35 | `d_AmountIncreaseValue` | DOUBLE |
| 36 | `d_AmountValueConstant` | I64 |
| 37 | `d_BonusAmountIncreaseRate` | I64 |
| 38 | `i_UnlockLevel` | I64 |
| 39 | `d_UnlockCost` | I64 |
| 40 | `i_RequirementFollowerId_1` | I64 |
| 41 | `i_RequirementFollowerId_2` | I64 |
| 42 | `i_RequirementMusicId_1` | I64 |
| 43 | `i_RequirementMusicId_2` | I64 |
| 44 | `i_RequirementMusicCount` | I64 |
| 45 | `s_GoodsType` | STRING |
| 46 | `i_SortOrder` | I64 |
| 47 | `i_AcquisitionType` | I64 |
| 48 | `i_AcquisitionId` | I64 |
| 49 | `b_IsActive` | I16 |
| 50 | `i_Area` | I16 |
| 51 | `i_DownloadType_img` | I32 |
| 52 | `i_DownloadType_file` | I32 |

### costume

| Thrift ID | Name | Type |
| --- | --- | --- |
| 1 | `i_id` | I32 |
| 2 | `s_Name_KO` | STRING |
| 3 | `s_Name_EN` | STRING |
| 4 | `s_Name_JA` | STRING |
| 5 | `s_Name_ZH_CHS` | STRING |
| 6 | `s_Name_ZH_CHT` | STRING |
| 7 | `s_Name_VI` | STRING |
| 8 | `s_Name_ES` | STRING |
| 9 | `s_Name_IT` | STRING |
| 10 | `s_Name_ID` | STRING |
| 11 | `s_Name_TH` | STRING |
| 12 | `s_Name_PT` | STRING |
| 13 | `s_Name_HI` | STRING |
| 14 | `s_Description_KO` | STRING |
| 15 | `s_Description_EN` | STRING |
| 16 | `s_Description_JA` | STRING |
| 17 | `s_Description_ZH_CHS` | STRING |
| 18 | `s_Description_ZH_CHT` | STRING |
| 19 | `s_Description_VI` | STRING |
| 20 | `s_Description_ES` | STRING |
| 21 | `s_Description_IT` | STRING |
| 22 | `s_Description_ID` | STRING |
| 23 | `s_Description_TH` | STRING |
| 24 | `s_Description_PT` | STRING |
| 25 | `s_Description_HI` | STRING |
| 26 | `s_ResourceName` | STRING |
| 27 | `s_CostumeName` | STRING |
| 28 | `i_MaxLevel` | I64 |
| 29 | `s_GoodsType` | STRING |
| 30 | `s_Cost` | STRING |
| 31 | `f_CostIncreaseRate` | DOUBLE |
| 32 | `s_Operation` | STRING |
| 33 | `d_Amount` | I64 |
| 34 | `f_AmountIncreaseRate` | DOUBLE |
| 35 | `s_BonusOperation` | STRING |
| 36 | `d_BonusAmount` | I64 |
| 37 | `f_BonusAmountIncreaseRate` | DOUBLE |
| 38 | `i_UnlockLevel` | I64 |
| 39 | `i_RequirementFollowerId_1` | I64 |
| 40 | `i_RequirementFollowerId_2` | I64 |
| 41 | `i_RequirementPropId_1` | I64 |
| 42 | `i_RequirementPropId_2` | I64 |
| 43 | `i_RequirementPropCount` | I64 |
| 44 | `i_SortOrder` | I64 |
| 45 | `f_FanMultiply` | DOUBLE |
| 46 | `i_AcquisitionType` | I64 |
| 47 | `i_AcquisitionId` | I64 |
| 48 | `b_IsActive` | I16 |
| 49 | `i_Area` | I16 |
| 50 | `i_DownloadType` | I16 |
| 51 | `s_AltCostumeName` | STRING |
| 52 | `s_AltCostumeStartTime` | STRING |
| 53 | `s_AltCostumeEndTime` | STRING |

### prop

| Thrift ID | Name | Type |
| --- | --- | --- |
| 1 | `i_id` | I32 |
| 2 | `s_Name_KO` | STRING |
| 3 | `s_Name_EN` | STRING |
| 4 | `s_Name_JA` | STRING |
| 5 | `s_Name_ZH_CHS` | STRING |
| 6 | `s_Name_ZH_CHT` | STRING |
| 7 | `s_Name_VI` | STRING |
| 8 | `s_Name_ES` | STRING |
| 9 | `s_Name_IT` | STRING |
| 10 | `s_Name_ID` | STRING |
| 11 | `s_Name_TH` | STRING |
| 12 | `s_Name_PT` | STRING |
| 13 | `s_Name_HI` | STRING |
| 14 | `s_Description_KO` | STRING |
| 15 | `s_Description_EN` | STRING |
| 16 | `s_Description_JA` | STRING |
| 17 | `s_Description_ZH_CHS` | STRING |
| 18 | `s_Description_ZH_CHT` | STRING |
| 19 | `s_Description_VI` | STRING |
| 20 | `s_Description_ES` | STRING |
| 21 | `s_Description_IT` | STRING |
| 22 | `s_Description_ID` | STRING |
| 23 | `s_Description_TH` | STRING |
| 24 | `s_Description_PT` | STRING |
| 25 | `s_Description_HI` | STRING |
| 26 | `s_ResourceName` | STRING |
| 27 | `i_RequirementPropId` | I64 |
| 28 | `i_Area` | I64 |
| 29 | `b_IsActive` | I64 |
| 30 | `i_MaxLevel` | I16 |

### follower

| Thrift ID | Name | Type |
| --- | --- | --- |
| 1 | `i_id` | I32 |
| 2 | `s_Name_KO` | STRING |
| 3 | `s_Name_EN` | STRING |
| 4 | `s_Name_JA` | STRING |
| 5 | `s_Name_ZH_CHS` | STRING |
| 6 | `s_Name_ZH_CHT` | STRING |
| 7 | `s_Name_VI` | STRING |
| 8 | `s_Name_ES` | STRING |
| 9 | `s_Name_IT` | STRING |
| 10 | `s_Name_ID` | STRING |
| 11 | `s_Name_TH` | STRING |
| 12 | `s_Name_PT` | STRING |
| 13 | `s_Name_HI` | STRING |
| 14 | `s_Description_KO` | STRING |
| 15 | `s_Description_EN` | STRING |
| 16 | `s_Description_JA` | STRING |
| 17 | `s_Description_ZH_CHS` | STRING |
| 18 | `s_Description_ZH_CHT` | STRING |
| 19 | `s_Description_VI` | STRING |
| 20 | `s_Description_ES` | STRING |
| 21 | `s_Description_IT` | STRING |
| 22 | `s_Description_ID` | STRING |
| 23 | `s_Description_TH` | STRING |
| 24 | `s_Description_PT` | STRING |
| 25 | `s_Description_HI` | STRING |
| 26 | `s_ResourceName` | STRING |
| 27 | `i_MaxLevel` | I64 |
| 28 | `d_LevelRate` | DOUBLE |
| 29 | `d_LateCost` | I64 |
| 30 | `d_Cost` | DOUBLE |
| 31 | `d_CostIncreaseValue` | DOUBLE |
| 32 | `d_CostValueConstant` | I64 |
| 33 | `d_Amount` | DOUBLE |
| 34 | `d_AmountIncreaseValue` | DOUBLE |
| 35 | `d_AmountValueConstant` | I64 |
| 36 | `d_BonusAmountIncreaseRate` | I64 |
| 37 | `i_UnlockLevel` | I64 |
| 38 | `d_UnlockCost` | I64 |
| 39 | `i_RequirementFollowerId_1` | I64 |
| 40 | `i_RequirementFollowerId_2` | I64 |
| 41 | `i_RequirementPropId_1` | I64 |
| 42 | `i_RequirementPropId_2` | I64 |
| 43 | `i_RequirementPropCount` | I64 |
| 44 | `b_IsActive` | I16 |
| 45 | `i_Area` | I16 |
| 46 | `i_DownloadType` | I32 |
| 47 | `i_ProfileID` | I32 |

### buff

| Thrift ID | Name | Type |
| --- | --- | --- |
| 1 | `i_id` | I32 |
| 2 | `s_ResourceName` | STRING |
| 3 | `s_Title_KO` | STRING |
| 4 | `s_Title_EN` | STRING |
| 5 | `s_Title_JA` | STRING |
| 6 | `s_Title_ZH_CHS` | STRING |
| 7 | `s_Title_ZH_CHT` | STRING |
| 8 | `s_Title_VI` | STRING |
| 9 | `s_Title_ES` | STRING |
| 10 | `s_Title_IT` | STRING |
| 11 | `s_Title_ID` | STRING |
| 12 | `s_Title_TH` | STRING |
| 13 | `s_Title_PT` | STRING |
| 14 | `s_Title_HI` | STRING |
| 15 | `s_Buff_Desc_KO` | STRING |
| 16 | `s_Buff_Desc_EN` | STRING |
| 17 | `s_Buff_Desc_JA` | STRING |
| 18 | `s_Buff_Desc_ZH_CHS` | STRING |
| 19 | `s_Buff_Desc_ZH_CHT` | STRING |
| 20 | `s_Buff_Desc_VI` | STRING |
| 21 | `s_Buff_Desc_ES` | STRING |
| 22 | `s_Buff_Desc_IT` | STRING |
| 23 | `s_Buff_Desc_ID` | STRING |
| 24 | `s_Buff_Desc_TH` | STRING |
| 25 | `s_Buff_Desc_PT` | STRING |
| 26 | `s_Buff_Desc_HI` | STRING |
| 27 | `i_Type` | I16 |
| 28 | `i_Retention_Time` | I64 |

### unit

| Thrift ID | Name | Type |
| --- | --- | --- |
| 1 | `i_id` | I32 |
| 2 | `s_Name_KO` | STRING |
| 3 | `s_Name_EN` | STRING |
| 4 | `s_Name_JA` | STRING |
| 5 | `s_Name_ZH_CHS` | STRING |
| 6 | `s_Name_ZH_CHT` | STRING |
| 7 | `s_Name_VI` | STRING |
| 8 | `s_Name_ES` | STRING |
| 9 | `s_Name_IT` | STRING |
| 10 | `s_Name_ID` | STRING |
| 11 | `s_Name_TH` | STRING |
| 12 | `s_Name_PT` | STRING |
| 13 | `s_Name_HI` | STRING |
| 14 | `s_Description_KO` | STRING |
| 15 | `s_Description_EN` | STRING |
| 16 | `s_Description_JA` | STRING |
| 17 | `s_Description_ZH_CHS` | STRING |
| 18 | `s_Description_ZH_CHT` | STRING |
| 19 | `s_Description_VI` | STRING |
| 20 | `s_Description_ES` | STRING |
| 21 | `s_Description_IT` | STRING |
| 22 | `s_Description_ID` | STRING |
| 23 | `s_Description_TH` | STRING |
| 24 | `s_Description_PT` | STRING |
| 25 | `s_Description_HI` | STRING |
| 26 | `s_ResourceName` | STRING |
| 27 | `i_MaxLevel` | I64 |
| 28 | `s_GoodsType` | STRING |
| 29 | `i_Cost` | DOUBLE |
| 30 | `f_CostIncreaseValue` | DOUBLE |
| 31 | `f_Value` | DOUBLE |
| 32 | `f_IncreaseValue` | DOUBLE |
| 33 | `i_UnlockLevel` | I64 |
| 34 | `i_UnlockCost` | I64 |
| 35 | `i_RequirementUnitId_1` | I64 |
| 36 | `i_RequirementUnitId_2` | I64 |
| 37 | `i_RequirementFollowerId_1` | I64 |
| 38 | `i_RequirementFollowerId_2` | I64 |
| 39 | `i_RequirementPropId_1` | I64 |
| 40 | `i_RequirementPropId_2` | I64 |
| 41 | `i_RequirementPropCount` | I64 |
| 42 | `i_Area` | I16 |
| 43 | `b_IsActive` | I16 |

### skill

| Thrift ID | Name | Type |
| --- | --- | --- |
| 1 | `i_id` | I32 |
| 2 | `i_Area` | I16 |
| 3 | `s_Name_KO` | STRING |
| 4 | `s_Name_EN` | STRING |
| 5 | `s_Name_JA` | STRING |
| 6 | `s_Name_ZH_CHS` | STRING |
| 7 | `s_Name_ZH_CHT` | STRING |
| 8 | `s_Name_VI` | STRING |
| 9 | `s_Name_ES` | STRING |
| 10 | `s_Name_IT` | STRING |
| 11 | `s_Name_ID` | STRING |
| 12 | `s_Name_TH` | STRING |
| 13 | `s_Name_PT` | STRING |
| 14 | `s_Name_HI` | STRING |
| 15 | `s_Description_KO` | STRING |
| 16 | `s_Description_EN` | STRING |
| 17 | `s_Description_JA` | STRING |
| 18 | `s_Description_ZH_CHS` | STRING |
| 19 | `s_Description_ZH_CHT` | STRING |
| 20 | `s_Description_VI` | STRING |
| 21 | `s_Description_ES` | STRING |
| 22 | `s_Description_IT` | STRING |
| 23 | `s_Description_ID` | STRING |
| 24 | `s_Description_TH` | STRING |
| 25 | `s_Description_PT` | STRING |
| 26 | `s_Description_HI` | STRING |
| 27 | `s_ResourceName` | STRING |
| 28 | `i_MaxLevel` | I64 |
| 29 | `s_GoodsType` | STRING |
| 30 | `i_Cost` | DOUBLE |
| 31 | `f_CostIncreaseValue` | DOUBLE |
| 32 | `f_SkillValue` | DOUBLE |
| 33 | `f_SkillIncreaseValue` | DOUBLE |
| 34 | `f_SkillTime` | DOUBLE |
| 35 | `f_SkillTimeIncreaseValue` | DOUBLE |
| 36 | `f_Cooltime` | DOUBLE |
| 37 | `i_UnlockLevel` | I64 |
| 38 | `i_UnlockCost` | I64 |
| 39 | `i_RequirementSkillId_1` | I64 |
| 40 | `i_RequirementSkillId_2` | I64 |
| 41 | `i_RequirementFollowerId_1` | I64 |
| 42 | `i_RequirementFollowerId_2` | I64 |
| 43 | `i_RequirementPropId_1` | I64 |
| 44 | `i_RequirementPropId_2` | I64 |
| 45 | `i_RequirementPropCount` | I64 |

### achievement

| Thrift ID | Name | Type |
| --- | --- | --- |
| 1 | `i_id` | I32 |
| 2 | `s_Title_KO` | STRING |
| 3 | `s_Title_EN` | STRING |
| 4 | `s_Title_JA` | STRING |
| 5 | `s_Title_ZH_CHS` | STRING |
| 6 | `s_Title_ZH_CHT` | STRING |
| 7 | `s_Title_VI` | STRING |
| 8 | `s_Title_ES` | STRING |
| 9 | `s_Title_IT` | STRING |
| 10 | `s_Title_ID` | STRING |
| 11 | `s_Title_TH` | STRING |
| 12 | `s_Title_PT` | STRING |
| 13 | `s_Title_HI` | STRING |
| 14 | `s_Description_KO` | STRING |
| 15 | `s_Description_EN` | STRING |
| 16 | `s_Description_JA` | STRING |
| 17 | `s_Description_ZH_CHS` | STRING |
| 18 | `s_Description_ZH_CHT` | STRING |
| 19 | `s_Description_VI` | STRING |
| 20 | `s_Description_ES` | STRING |
| 21 | `s_Description_IT` | STRING |
| 22 | `s_Description_ID` | STRING |
| 23 | `s_Description_TH` | STRING |
| 24 | `s_Description_PT` | STRING |
| 25 | `s_Description_HI` | STRING |
| 26 | `s_ResourceName` | STRING |
| 27 | `s_AchievementConditionType` | STRING |
| 28 | `s_RewardType` | STRING |
| 29 | `s_RewardDescription_KO` | STRING |
| 30 | `s_RewardDescription_EN` | STRING |
| 31 | `s_RewardDescription_JA` | STRING |
| 32 | `s_RewardDescription_ZH_CHS` | STRING |
| 33 | `s_RewardDescription_ZH_CHT` | STRING |
| 34 | `s_RewardDescription_VI` | STRING |
| 35 | `s_RewardDescription_ES` | STRING |
| 36 | `s_RewardDescription_IT` | STRING |
| 37 | `s_RewardDescription_ID` | STRING |
| 38 | `s_RewardDescription_TH` | STRING |
| 39 | `s_RewardDescription_PT` | STRING |
| 40 | `s_RewardDescription_HI` | STRING |
| 41 | `i_Reward_1` | I64 |
| 42 | `i_Reward_2` | I64 |
| 43 | `i_Reward_3` | I64 |
| 44 | `i_Reward_4` | I64 |
| 45 | `i_Reward_5` | I64 |
| 46 | `i_Reward_6` | I64 |
| 47 | `i_Reward_7` | I64 |
| 48 | `i_Reward_8` | I64 |
| 49 | `i_Reward_9` | I64 |
| 50 | `i_Reward_10` | I64 |
| 51 | `i_Area` | I16 |
| 52 | `b_IsActive` | I16 |
| 53 | `i_Reward_11` | I64 |
| 54 | `i_Reward_12` | I64 |
| 55 | `i_MaxLevel` | I16 |
| 56 | `s_Condition_1` | STRING |
| 57 | `s_Condition_2` | STRING |
| 58 | `s_Condition_3` | STRING |
| 59 | `s_Condition_4` | STRING |
| 60 | `s_Condition_5` | STRING |
| 61 | `s_Condition_6` | STRING |
| 62 | `s_Condition_7` | STRING |
| 63 | `s_Condition_8` | STRING |
| 64 | `s_Condition_9` | STRING |
| 65 | `s_Condition_10` | STRING |
| 66 | `s_Condition_11` | STRING |
| 67 | `s_Condition_12` | STRING |
| 68 | `s_Condition_13` | STRING |
| 69 | `s_Condition_14` | STRING |
| 70 | `s_Condition_15` | STRING |
| 71 | `s_Condition_16` | STRING |
| 72 | `s_Condition_17` | STRING |
| 73 | `s_Condition_18` | STRING |
| 74 | `s_Condition_19` | STRING |
| 75 | `s_Condition_20` | STRING |
| 76 | `i_Reward_13` | I64 |
| 77 | `i_Reward_14` | I64 |
| 78 | `i_Reward_15` | I64 |
| 79 | `i_Reward_16` | I64 |
| 80 | `i_Reward_17` | I64 |
| 81 | `i_Reward_18` | I64 |
| 82 | `i_Reward_19` | I64 |
| 83 | `i_Reward_20` | I64 |

### daily_mission

| Thrift ID | Name | Type |
| --- | --- | --- |
| 1 | `i_id` | I32 |
| 2 | `s_Title_KO` | STRING |
| 3 | `s_Title_EN` | STRING |
| 4 | `s_Title_JA` | STRING |
| 5 | `s_Title_ZH_CHS` | STRING |
| 6 | `s_Title_ZH_CHT` | STRING |
| 7 | `s_Title_VI` | STRING |
| 8 | `s_Title_ES` | STRING |
| 9 | `s_Title_IT` | STRING |
| 10 | `s_Title_ID` | STRING |
| 11 | `s_Title_TH` | STRING |
| 12 | `s_Title_PT` | STRING |
| 13 | `s_Title_HI` | STRING |
| 14 | `s_Description_KO` | STRING |
| 15 | `s_Description_EN` | STRING |
| 16 | `s_Description_JA` | STRING |
| 17 | `s_Description_ZH_CHS` | STRING |
| 18 | `s_Description_ZH_CHT` | STRING |
| 19 | `s_Description_VI` | STRING |
| 20 | `s_Description_ES` | STRING |
| 21 | `s_Description_IT` | STRING |
| 22 | `s_Description_ID` | STRING |
| 23 | `s_Description_TH` | STRING |
| 24 | `s_Description_PT` | STRING |
| 25 | `s_Description_HI` | STRING |
| 26 | `s_ResourceName` | STRING |
| 27 | `s_DailyMissionConditionType` | STRING |
| 28 | `d_Condition_1` | DOUBLE |
| 29 | `s_RewardType` | STRING |
| 30 | `s_RewardDescription_KO` | STRING |
| 31 | `s_RewardDescription_EN` | STRING |
| 32 | `s_RewardDescription_JA` | STRING |
| 33 | `s_RewardDescription_ZH_CHS` | STRING |
| 34 | `s_RewardDescription_ZH_CHT` | STRING |
| 35 | `s_RewardDescription_VI` | STRING |
| 36 | `s_RewardDescription_ES` | STRING |
| 37 | `s_RewardDescription_IT` | STRING |
| 38 | `s_RewardDescription_ID` | STRING |
| 39 | `s_RewardDescription_TH` | STRING |
| 40 | `s_RewardDescription_PT` | STRING |
| 41 | `s_RewardDescription_HI` | STRING |
| 42 | `i_Reward_1` | I32 |
| 43 | `i_Area` | I16 |
| 44 | `b_IsActive` | I16 |

### music_level

| Thrift ID | Name | Type |
| --- | --- | --- |
| 1 | `i_Level` | I16 |
| 2 | `f_EncoreBonusAppearRate` | DOUBLE |
| 3 | `i_EncoreBonusAppearPercent` | I64 |
| 4 | `f_EncoreBonusAppearCooltime_Sec` | DOUBLE |
| 5 | `f_EncoreBonusAppearCooltime_Hour` | DOUBLE |
| 6 | `i_EncoreBonusGiftAmount` | I16 |
| 7 | `i_EncoreFollowerProfileExp` | I32 |
| 8 | `i_ChThirdCoolTime` | I32 |

### shop

| Thrift ID | Name | Type |
| --- | --- | --- |
| 1 | `i_id` | I64 |
| 2 | `s_ProductID_ios` | STRING |
| 3 | `s_ProductID_aos` | STRING |
| 4 | `i_ShopCategory` | I64 |
| 5 | `i_ProductType` | I64 |
| 6 | `s_ResourceName` | STRING |
| 7 | `s_Title_KO` | STRING |
| 8 | `s_Title_EN` | STRING |
| 9 | `s_Title_JA` | STRING |
| 10 | `s_Title_ZH_CHS` | STRING |
| 11 | `s_Title_ZH_CHT` | STRING |
| 12 | `s_Title_VI` | STRING |
| 13 | `s_Title_ES` | STRING |
| 14 | `s_Title_IT` | STRING |
| 15 | `s_Title_ID` | STRING |
| 16 | `s_Title_TH` | STRING |
| 17 | `s_Title_PT` | STRING |
| 18 | `s_Title_HI` | STRING |
| 19 | `s_Description_KO` | STRING |
| 20 | `s_Description_EN` | STRING |
| 21 | `s_Description_JA` | STRING |
| 22 | `s_Description_ZH_CHS` | STRING |
| 23 | `s_Description_ZH_CHT` | STRING |
| 24 | `s_Description_VI` | STRING |
| 25 | `s_Description_ES` | STRING |
| 26 | `s_Description_IT` | STRING |
| 27 | `s_Description_ID` | STRING |
| 28 | `s_Description_TH` | STRING |
| 29 | `s_Description_PT` | STRING |
| 30 | `s_Description_HI` | STRING |
| 31 | `i_RewardGroup` | I64 |
| 32 | `i_Tag` | I64 |
| 33 | `i_SellType` | I64 |
| 34 | `i_SellValue` | I64 |
| 35 | `b_IsActive` | I16 |
| 36 | `i_Condition` | I64 |
| 37 | `i_ConditionValue` | I64 |
| 38 | `s_StorePrice_AOS` | STRING |
| 39 | `s_StorePrice_IOS` | STRING |
| 40 | `i_SortIndex` | I16 |
| 41 | `s_AreaList` | STRING |
| 42 | `s_AltResourceName` | STRING |
| 43 | `s_AltDescription_KO` | STRING |
| 44 | `s_AltDescription_EN` | STRING |
| 45 | `s_AltDescription_JA` | STRING |
| 46 | `s_AltDescription_ZH_CHS` | STRING |
| 47 | `s_AltDescription_ZH_CHT` | STRING |
| 48 | `s_AltDescription_VI` | STRING |
| 49 | `s_AltDescription_ES` | STRING |
| 50 | `s_AltDescription_IT` | STRING |
| 51 | `s_AltDescription_ID` | STRING |
| 52 | `s_AltDescription_TH` | STRING |
| 53 | `s_AltDescription_PT` | STRING |
| 54 | `s_AltDescription_HI` | STRING |
| 55 | `s_Kor_StorePrice_AOS` | STRING |
| 56 | `s_Kor_StorePrice_IOS` | STRING |
| 57 | `b_IsLimitTime` | I16 |
| 58 | `s_UIStartTime` | STRING |
| 59 | `s_StartTime` | STRING |
| 60 | `s_EndTime` | STRING |

### reward_group

| Thrift ID | Name | Type |
| --- | --- | --- |
| 1 | `i_id` | I64 |
| 2 | `i_Group` | I64 |
| 3 | `i_RewardType` | I64 |
| 4 | `i_RewardID` | I64 |
| 5 | `l_RewardQuantity` | I64 |
| 6 | `i_BuyFirstQuantity` | I64 |

### Fan

| Thrift ID | Name | Type |
| --- | --- | --- |
| 1 | `i_Area` | I64 |
| 2 | `i_Grade` | I64 |
| 3 | `i_FanCount` | I64 |
| 4 | `i_BonusRate` | I64 |
| 5 | `i_BonusRateUI` | I64 |

### SystemNotification

| Thrift ID | Name | Type |
| --- | --- | --- |
| 1 | `i_Id` | I64 |
| 2 | `s_DescriptionType` | STRING |
| 3 | `i_Type` | STRING |
| 4 | `s_Factor` | STRING |
| 5 | `s_Description_KO` | STRING |
| 6 | `s_Description_EN` | STRING |
| 7 | `s_Description_JA` | STRING |
| 8 | `s_Description_ZH_CHS` | STRING |
| 9 | `s_Description_ZH_CHT` | STRING |
| 10 | `s_Description_VI` | STRING |
| 11 | `s_Description_ES` | STRING |
| 12 | `s_Description_IT` | STRING |
| 13 | `s_Description_ID` | STRING |
| 14 | `s_Description_TH` | STRING |
| 15 | `s_Description_PT` | STRING |
| 16 | `s_Description_HI` | STRING |

### SystemString

| Thrift ID | Name | Type |
| --- | --- | --- |
| 1 | `i_StringID` | I64 |
| 2 | `s_Category` | STRING |
| 3 | `s_UIType` | STRING |
| 4 | `s_Key` | STRING |
| 5 | `s_KO` | STRING |
| 6 | `s_EN` | STRING |
| 7 | `s_JA` | STRING |
| 8 | `s_ZH_CHS` | STRING |
| 9 | `s_ZH_CHT` | STRING |
| 10 | `s_ID` | STRING |
| 11 | `s_PT` | STRING |
| 12 | `s_ES` | STRING |
| 13 | `s_RU` | STRING |
| 14 | `s_DE` | STRING |
| 15 | `s_AR_XA` | STRING |
| 16 | `s_VI` | STRING |
| 17 | `s_IT` | STRING |
| 18 | `s_TH` | STRING |
| 19 | `s_HI` | STRING |

### SubscribeList

| Thrift ID | Name | Type |
| --- | --- | --- |
| 1 | `i_id` | I64 |
| 2 | `i_Area` | I16 |
| 3 | `s_Type` | STRING |
| 4 | `i_TimeLimit` | I16 |
| 7 | `b_IsActive` | I16 |
| 11 | `i_StartYear` | I32 |
| 12 | `i_RepeatMonth` | I32 |
| 13 | `i_MonthGroupIndex` | I32 |

### SubscribePassReward

| Thrift ID | Name | Type |
| --- | --- | --- |
| 1 | `i_id` | I64 |
| 2 | `i_Group` | I64 |
| 3 | `i_Step` | I16 |
| 4 | `i_Goal` | I64 |
| 5 | `i_FreeRewardGroup` | I64 |
| 6 | `i_PaidRewardGroup` | I64 |

### SubscribePass

| Thrift ID | Name | Type |
| --- | --- | --- |
| 1 | `i_id` | I64 |
| 2 | `i_SubscribeID` | I64 |
| 3 | `s_AcquireList` | STRING |
| 4 | `i_PointPrice` | I16 |
| 5 | `i_PaidPoint` | I64 |
| 6 | `i_ActiveBuffID` | I64 |
| 7 | `i_HiddenStep` | I64 |
| 8 | `i_ADPoint` | I64 |
| 9 | `i_ADCoolTime` | I64 |
| 10 | `i_TicketCollectionId` | I64 |

### Guitar

| Thrift ID | Name | Type |
| --- | --- | --- |
| 1 | `i_id` | I32 |
| 2 | `i_Area` | I16 |
| 3 | `s_Title_KO` | STRING |
| 4 | `s_Title_EN` | STRING |
| 5 | `s_Title_JA` | STRING |
| 6 | `s_Title_ZH_CHS` | STRING |
| 7 | `s_Title_ZH_CHT` | STRING |
| 8 | `s_Title_VI` | STRING |
| 9 | `s_Title_ES` | STRING |
| 10 | `s_Title_IT` | STRING |
| 11 | `s_Title_ID` | STRING |
| 12 | `s_Title_TH` | STRING |
| 13 | `s_Title_PT` | STRING |
| 14 | `s_Title_HI` | STRING |
| 15 | `s_Description_KO` | STRING |
| 16 | `s_Description_EN` | STRING |
| 17 | `s_Description_JA` | STRING |
| 18 | `s_Description_ZH_CHS` | STRING |
| 19 | `s_Description_ZH_CHT` | STRING |
| 20 | `s_Description_VI` | STRING |
| 21 | `s_Description_ES` | STRING |
| 22 | `s_Description_IT` | STRING |
| 23 | `s_Description_ID` | STRING |
| 24 | `s_Description_TH` | STRING |
| 25 | `s_Description_PT` | STRING |
| 26 | `s_Description_HI` | STRING |
| 27 | `s_ResourceName` | STRING |
| 28 | `s_GuitarName` | STRING |
| 29 | `i_GuitarType` | I16 |
| 30 | `s_GoodsType` | STRING |
| 31 | `s_Cost` | STRING |
| 32 | `i_RequirementCharacterLevel` | I64 |
| 33 | `d_IncrementValue` | DOUBLE |
| 34 | `i_AcquisitionType` | I64 |
| 35 | `i_AcquisitionId` | I64 |
| 36 | `i_SortOrder` | I64 |
| 37 | `b_IsActive` | I16 |
| 38 | `i_DownloadType` | I16 |

### SubscribePassRewardInformation

| Thrift ID | Name | Type |
| --- | --- | --- |
| 1 | `i_id` | I32 |
| 2 | `s_ResourceName` | STRING |
| 3 | `s_Description_KO` | STRING |
| 4 | `s_Description_EN` | STRING |
| 5 | `s_Description_JA` | STRING |
| 6 | `s_Description_ZH_CHS` | STRING |
| 7 | `s_Description_ZH_CHT` | STRING |
| 8 | `s_Description_VI` | STRING |
| 9 | `s_Description_ES` | STRING |
| 10 | `s_Description_IT` | STRING |
| 11 | `s_Description_ID` | STRING |
| 12 | `s_Description_TH` | STRING |
| 13 | `s_Description_PT` | STRING |
| 14 | `s_Description_HI` | STRING |
| 15 | `b_IsActive` | I16 |

### ticketcollection

| Thrift ID | Name | Type |
| --- | --- | --- |
| 1 | `i_id` | I32 |
| 2 | `s_TicketType` | STRING |
| 3 | `s_Title_KO` | STRING |
| 4 | `s_Title_EN` | STRING |
| 5 | `s_Title_JA` | STRING |
| 6 | `s_Title_ZH_CHS` | STRING |
| 7 | `s_Title_ZH_CHT` | STRING |
| 8 | `s_Title_VI` | STRING |
| 9 | `s_Title_ES` | STRING |
| 10 | `s_Title_IT` | STRING |
| 11 | `s_Title_ID` | STRING |
| 12 | `s_Title_TH` | STRING |
| 13 | `s_Title_PT` | STRING |
| 14 | `s_Title_HI` | STRING |
| 15 | `s_Description_KO` | STRING |
| 16 | `s_Description_EN` | STRING |
| 17 | `s_Description_JA` | STRING |
| 18 | `s_Description_ZH_CHS` | STRING |
| 19 | `s_Description_ZH_CHT` | STRING |
| 20 | `s_Description_VI` | STRING |
| 21 | `s_Description_ES` | STRING |
| 22 | `s_Description_IT` | STRING |
| 23 | `s_Description_ID` | STRING |
| 24 | `s_Description_TH` | STRING |
| 25 | `s_Description_PT` | STRING |
| 26 | `s_Description_HI` | STRING |
| 27 | `s_ResourceName` | STRING |
| 28 | `s_ResourceName_Big` | STRING |
| 29 | `i_Season` | I16 |
| 30 | `s_PassUIBundleName` | STRING |
| 31 | `s_BackgroundColor` | STRING |
| 32 | `s_LabelColor` | STRING |
| 33 | `s_SeasonLabelColor` | STRING |
| 34 | `s_SeasonBackColor` | STRING |
| 35 | `i_SortOrder` | I32 |
| 36 | `b_IsActive` | I16 |

### character

| Thrift ID | Name | Type |
| --- | --- | --- |
| 1 | `i_id` | I32 |
| 2 | `i_Area` | I16 |
| 3 | `s_BundleName` | STRING |
| 4 | `s_Name_KO` | STRING |
| 5 | `s_Name_EN` | STRING |
| 6 | `s_Name_JA` | STRING |
| 7 | `s_Name_ZH_CHS` | STRING |
| 8 | `s_Name_ZH_CHT` | STRING |
| 9 | `s_Name_VI` | STRING |
| 10 | `s_Name_ES` | STRING |
| 11 | `s_Name_IT` | STRING |
| 12 | `s_Name_ID` | STRING |
| 13 | `s_Name_TH` | STRING |
| 14 | `s_Name_PT` | STRING |
| 15 | `s_Name_HI` | STRING |
| 16 | `s_Description_KO` | STRING |
| 17 | `s_Description_EN` | STRING |
| 18 | `s_Description_JA` | STRING |
| 19 | `s_Description_ZH_CHS` | STRING |
| 20 | `s_Description_ZH_CHT` | STRING |
| 21 | `s_Description_VI` | STRING |
| 22 | `s_Description_ES` | STRING |
| 23 | `s_Description_IT` | STRING |
| 24 | `s_Description_ID` | STRING |
| 25 | `s_Description_TH` | STRING |
| 26 | `s_Description_PT` | STRING |
| 27 | `s_Description_HI` | STRING |
| 28 | `s_ResourceName` | STRING |
| 29 | `i_MaxLevel` | I64 |
| 30 | `d_LevelRate` | DOUBLE |
| 31 | `d_LateCost` | DOUBLE |
| 32 | `d_Cost` | DOUBLE |
| 33 | `d_CostIncreaseValue` | DOUBLE |
| 34 | `d_CostValueConstant` | DOUBLE |
| 35 | `d_Amount` | DOUBLE |
| 36 | `d_AmountIncreaseValue` | DOUBLE |
| 37 | `d_AmountValueConstant` | DOUBLE |
| 38 | `d_BonusAmountIncreaseRate` | DOUBLE |
| 39 | `i_UnlockLevel` | I64 |
| 40 | `d_UnlockCost` | DOUBLE |
| 41 | `i_RequirementFollowerId_1` | I64 |
| 42 | `i_RequirementFollowerId_2` | I64 |
| 43 | `i_RequirementPropId_1` | I64 |
| 44 | `i_RequirementPropId_2` | I64 |
| 45 | `i_RequirementPropCount` | I64 |
| 46 | `b_IsActive` | I16 |

### samseckevent

| Thrift ID | Name | Type |
| --- | --- | --- |
| 1 | `i_id` | I32 |
| 2 | `s_Description_KO` | STRING |
| 3 | `s_Description_EN` | STRING |
| 4 | `s_Description_JA` | STRING |
| 5 | `s_Description_ZH_CHS` | STRING |
| 6 | `s_Description_ZH_CHT` | STRING |
| 7 | `s_Description_VI` | STRING |
| 8 | `s_Description_ES` | STRING |
| 9 | `s_Description_IT` | STRING |
| 10 | `s_Description_ID` | STRING |
| 11 | `s_Description_TH` | STRING |
| 12 | `s_Description_PT` | STRING |
| 13 | `s_Description_HI` | STRING |
| 14 | `s_ConditionType` | STRING |
| 15 | `d_Condition` | DOUBLE |
| 16 | `i_MailRewardID` | I64 |
| 17 | `b_IsActive` | I16 |

### localpush

| Thrift ID | Name | Type |
| --- | --- | --- |
| 1 | `i_id` | I32 |
| 2 | `s_LocalPushRegisterType` | STRING |
| 3 | `i_TimeForSeconds` | I64 |
| 4 | `b_IsMultipleJson` | I16 |
| 5 | `s_JsonMessage_KO` | STRING |
| 6 | `s_JsonMessage_EN` | STRING |
| 7 | `s_JsonMessage_JA` | STRING |
| 8 | `s_JsonMessage_ZH_CHS` | STRING |
| 9 | `s_JsonMessage_ZH_CHT` | STRING |
| 10 | `s_JsonMessage_VI` | STRING |
| 11 | `s_JsonMessage_ES` | STRING |
| 12 | `s_JsonMessage_IT` | STRING |
| 13 | `s_JsonMessage_ID` | STRING |
| 14 | `s_JsonMessage_TH` | STRING |
| 15 | `s_JsonMessage_PT` | STRING |
| 16 | `s_JsonMessage_HI` | STRING |
| 17 | `b_IsActive` | I16 |

### followerquest

| Thrift ID | Name | Type |
| --- | --- | --- |
| 1 | `i_id` | I32 |
| 2 | `i_UnlockFollowerID` | I32 |
| 3 | `i_UnlockFollowerLevel` | I32 |
| 4 | `s_ConditionType1` | STRING |
| 5 | `d_Condition1_1` | DOUBLE |
| 6 | `d_Condition1_2` | DOUBLE |
| 7 | `s_ConditionType2` | STRING |
| 8 | `d_Condition2_1` | DOUBLE |
| 9 | `d_Condition2_2` | DOUBLE |
| 10 | `s_ConditionType3` | STRING |
| 11 | `d_Condition3_1` | DOUBLE |
| 12 | `d_Condition3_2` | DOUBLE |
| 13 | `i_RewardGroup1` | I32 |
| 14 | `i_RewardGroup2` | I32 |
| 15 | `i_RewardGroup3` | I32 |
| 16 | `s_Description_KO` | STRING |
| 17 | `s_Description_EN` | STRING |
| 18 | `s_Description_ZH_CHS` | STRING |
| 19 | `s_Description_ZH_CHT` | STRING |
| 20 | `s_Description_JA` | STRING |
| 21 | `s_Description_VI` | STRING |
| 22 | `s_Description_ES` | STRING |
| 23 | `s_Description_IT` | STRING |
| 24 | `s_Description_ID` | STRING |
| 25 | `s_Description_TH` | STRING |
| 26 | `s_Description_PT` | STRING |
| 27 | `s_Description_HI` | STRING |
| 28 | `b_IsActive` | I16 |
| 29 | `i_Type` | I32 |

### proplevel

| Thrift ID | Name | Type |
| --- | --- | --- |
| 1 | `i_id` | I32 |
| 2 | `i_PropId` | I64 |
| 3 | `i_Level` | I64 |
| 4 | `d_Cost` | DOUBLE |
| 5 | `i_PerksId` | I64 |
| 6 | `d_PerksValue` | DOUBLE |
| 7 | `b_IsActive` | I16 |

### follower_profile

| Thrift ID | Name | Type |
| --- | --- | --- |
| 1 | `i_id` | I32 |
| 2 | `s_Name_KO` | STRING |
| 3 | `s_Name_EN` | STRING |
| 4 | `s_Name_JA` | STRING |
| 5 | `s_Name_ZH_CHS` | STRING |
| 6 | `s_Name_ZH_CHT` | STRING |
| 7 | `s_Name_VI` | STRING |
| 8 | `s_Name_ES` | STRING |
| 9 | `s_Name_IT` | STRING |
| 10 | `s_Name_ID` | STRING |
| 11 | `s_Name_TH` | STRING |
| 12 | `s_Name_PT` | STRING |
| 13 | `s_Name_HI` | STRING |
| 14 | `b_IsActive` | I16 |
| 15 | `s_GiftItemID` | STRING |
| 16 | `b_IsVisible` | I16 |
| 17 | `s_BackgroundColor` | STRING |

### passgoodsshop

| Thrift ID | Name | Type |
| --- | --- | --- |
| 1 | `i_id` | I32 |
| 2 | `i_TicketID` | I32 |
| 3 | `i_GoodsTicketID` | I32 |
| 4 | `i_ShopID` | I32 |
| 5 | `b_IsActive` | I16 |
| 6 | `i_SaleShopID` | I32 |

### followergiftitem

| Thrift ID | Name | Type |
| --- | --- | --- |
| 1 | `i_id` | I32 |
| 2 | `i_GiftType` | I32 |
| 3 | `d_Value` | I64 |
| 4 | `i_Limit` | I32 |
| 5 | `s_ResourceName` | STRING |
| 6 | `s_Name_KO` | STRING |
| 7 | `s_Name_EN` | STRING |
| 8 | `s_Name_JA` | STRING |
| 9 | `s_Name_ZH_CHS` | STRING |
| 10 | `s_Name_ZH_CHT` | STRING |
| 11 | `s_Name_VI` | STRING |
| 12 | `s_Name_ES` | STRING |
| 13 | `s_Name_IT` | STRING |
| 14 | `s_Name_ID` | STRING |
| 15 | `s_Name_TH` | STRING |
| 16 | `s_Name_PT` | STRING |
| 17 | `s_Name_HI` | STRING |
| 18 | `b_IsActive` | I16 |

### followerprofilelevel

| Thrift ID | Name | Type |
| --- | --- | --- |
| 1 | `i_id` | I32 |
| 2 | `i_ProfileID` | I32 |
| 3 | `i_Level` | I32 |
| 4 | `d_RequireEXP` | I64 |
| 5 | `i_RewardGroup` | I32 |
| 6 | `s_UnlockInformation` | STRING |
| 7 | `i_AddCandy` | I32 |
| 8 | `i_UnlockStoryID` | I32 |
| 9 | `b_IsActive` | I16 |

### ad_list

| Thrift ID | Name | Type |
| --- | --- | --- |
| 1 | `i_id` | I32 |
| 2 | `i_Category` | I32 |
| 3 | `s_ConditionType1` | STRING |
| 4 | `s_ConditionValue1` | STRING |
| 5 | `s_ConditionType2` | STRING |
| 6 | `s_ConditionValue2` | STRING |
| 7 | `s_ResourceName` | STRING |
| 8 | `s_Name_KO` | STRING |
| 9 | `s_Name_EN` | STRING |
| 10 | `s_Name_JA` | STRING |
| 11 | `s_Name_ZH_CHS` | STRING |
| 12 | `s_Name_ZH_CHT` | STRING |
| 13 | `s_Name_VI` | STRING |
| 14 | `s_Name_ES` | STRING |
| 15 | `s_Name_IT` | STRING |
| 16 | `s_Name_ID` | STRING |
| 17 | `s_Name_TH` | STRING |
| 18 | `s_Name_PT` | STRING |
| 19 | `s_Name_HI` | STRING |
| 20 | `b_IsActive` | I16 |
| 21 | `s_RewardType` | STRING |
| 22 | `i_RewardGroup` | I32 |
| 23 | `s_ExtraValue` | STRING |
| 24 | `s_AdType` | STRING |

### chthird_stage

| Thrift ID | Name | Type |
| --- | --- | --- |
| 1 | `i_id` | I32 |
| 2 | `i_Chapter` | I32 |
| 3 | `i_StageIndex` | I32 |
| 4 | `i_RewardGroupID` | I32 |
| 5 | `i_GoalScore1` | I32 |
| 6 | `i_GoalScore2` | I32 |
| 7 | `i_GoalScore3` | I32 |
| 8 | `s_BonusProfileID` | STRING |
| 9 | `s_Name_KO` | STRING |
| 10 | `s_Name_EN` | STRING |
| 11 | `s_Name_JA` | STRING |
| 12 | `s_Name_ZH_CHS` | STRING |
| 13 | `s_Name_ZH_CHT` | STRING |
| 14 | `s_Name_VI` | STRING |
| 15 | `s_Name_ES` | STRING |
| 16 | `s_Name_IT` | STRING |
| 17 | `s_Name_ID` | STRING |
| 18 | `s_Name_TH` | STRING |
| 19 | `s_Name_PT` | STRING |
| 20 | `s_Name_HI` | STRING |
| 21 | `s_Description_KO` | STRING |
| 22 | `s_Description_EN` | STRING |
| 23 | `s_Description_JA` | STRING |
| 24 | `s_Description_ZH_CHS` | STRING |
| 25 | `s_Description_ZH_CHT` | STRING |
| 26 | `s_Description_VI` | STRING |
| 27 | `s_Description_ES` | STRING |
| 28 | `s_Description_IT` | STRING |
| 29 | `s_Description_ID` | STRING |
| 30 | `s_Description_TH` | STRING |
| 31 | `s_Description_PT` | STRING |
| 32 | `s_Description_HI` | STRING |
| 33 | `b_IsActive` | I16 |
| 34 | `s_StageType` | STRING |
| 35 | `i_StoryID` | I32 |
| 36 | `i_BonusMusicID` | I32 |
| 37 | `s_PercentRewardGroupID` | STRING |

### chthird_score

| Thrift ID | Name | Type |
| --- | --- | --- |
| 1 | `i_id` | I32 |
| 2 | `i_Level` | I32 |
| 3 | `i_CharacterScore` | I32 |
| 4 | `i_FollowerScore` | I32 |
| 5 | `i_MusicScore` | I32 |
| 6 | `b_IsActive` | I16 |

### chthird_chapter

| Thrift ID | Name | Type |
| --- | --- | --- |
| 1 | `i_id` | I32 |
| 2 | `i_unlockLevel` | I32 |
| 3 | `i_RewardGroupID1` | I32 |
| 4 | `i_GoalStar1` | I32 |
| 5 | `i_RewardGroupID2` | I32 |
| 6 | `i_GoalStar2` | I32 |
| 7 | `i_RewardGroupID3` | I32 |
| 8 | `i_GoalStar3` | I32 |
| 9 | `s_Name_KO` | STRING |
| 10 | `s_Name_EN` | STRING |
| 11 | `s_Name_JA` | STRING |
| 12 | `s_Name_ZH_CHS` | STRING |
| 13 | `s_Name_ZH_CHT` | STRING |
| 14 | `s_Name_VI` | STRING |
| 15 | `s_Name_ES` | STRING |
| 16 | `s_Name_IT` | STRING |
| 17 | `s_Name_ID` | STRING |
| 18 | `s_Name_TH` | STRING |
| 19 | `s_Name_PT` | STRING |
| 20 | `s_Name_HI` | STRING |
| 21 | `b_IsActive` | I16 |

### percent

| Thrift ID | Name | Type |
| --- | --- | --- |
| 1 | `i_GroupID` | I32 |
| 2 | `i_RewardType` | I32 |
| 3 | `i_RewardID` | I32 |
| 4 | `l_RewardQuantity` | I32 |
| 5 | `b_IsActive` | I16 |
| 6 | `i_id` | I32 |

### ad_level

| Thrift ID | Name | Type |
| --- | --- | --- |
| 1 | `i_GroupID` | I32 |
| 2 | `i_Level` | I32 |
| 3 | `i_RequireEXP` | I32 |
| 4 | `i_RewardGroup` | I32 |
| 5 | `b_IsActive` | I16 |
| 6 | `i_id` | I32 |

### event_list

| Thrift ID | Name | Type |
| --- | --- | --- |
| 1 | `idx` | I32 |
| 2 | `event_type` | STRING |
| 3 | `start_date` | STRING |
| 4 | `end_date` | STRING |
| 5 | `b_IsActive` | I16 |

### select_reward

| Thrift ID | Name | Type |
| --- | --- | --- |
| 1 | `i_id` | I32 |
| 2 | `i_GroupId` | I32 |
| 3 | `i_RewardGroupId` | I32 |
| 4 | `i_AltRewardGroupId` | I32 |
| 5 | `b_IsActive` | I16 |
