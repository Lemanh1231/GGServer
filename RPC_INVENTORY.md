# Danh mục toàn bộ RPC native

Nguồn: `resources/schema/schema.json` + đăng ký runtime `GameContext`.
**134 wire route, 129 tên đơn**; handler65 route/61 tên, fallback69 route/68 tên.
`legacy-fallback` trả success với object rỗng trước encode; không thực hiện gameplay.
Owner là module cài handler, không phải bằng chứng logic đầy đủ. Các handler stub
và unsupported được giải thích trong `RPC_LOGIC_AUDIT.md`.

Mỗi tên trong bảng ghép với namespace ở cột đầu để có full wire command.

| Namespace | Owner | Số route | Tên đơn |
| --- | --- | ---: | --- |
| eventMode | content | 5 | `eventRewardList`, `getEventMain`, `getEventRank`, `getSamSeckList`, `getSamSeckReward` |
| main | auth | 5 | `Request`, `defaultSettingList`, `getLocalPush`, `getServerTime`, `getUpdateTime` |
| main | content | 1 | `getGameDataList` |
| main | economy | 1 | `getEventRewardList` |
| main | legacy-fallback | 9 | `avatarList`, `getCollection`, `getNoticeList`, `getTabList`, `main`, `moreGames`, `newStoreList`, `storeList`, `titleList` |
| multi | legacy-fallback | 1 | `getServerList` |
| music | legacy-fallback | 7 | `getAlbum`, `getAlbumInfoList`, `getAlbumList`, `getCache`, `getMusicInfoList`, `getMusicList`, `getReviewPoint` |
| post | social | 5 | `deletePost`, `getPost`, `getPostTime`, `providePost`, `readPost` |
| rank | legacy-fallback | 7 | `getCountryMyRank`, `getCountryRank`, `getMastersRank`, `getMusicRank`, `getRankMain`, `getTotalCountryRank`, `getTotalMusicRank` |
| store | content | 1 | `getVarietyStore` |
| store | economy | 4 | `buyCheck`, `buyContents`, `buyShop`, `buyVarietyStore` |
| store | legacy-fallback | 3 | `itemStoreList`, `storeList`, `storeNotice` |
| tour | content | 1 | `playMusic` |
| tour | legacy-fallback | 5 | `endPlayMusic`, `getTourList`, `getTourRank`, `playCheck`, `tourMain` |
| tour | social | 1 | `getPostTime` |
| user | auth | 14 | `completeLog`, `getProfile`, `hibernationLog`, `lastSaveTime`, `setReviewPopup`, `setSubscribe`, `setTutorialNew`, `updateAvatar`, `updateNickName`, `updateUserTitle`, `userJoin`, `userLoad`, `userLogin`, `userSave` |
| user | content | 8 | `chThirdStage`, `chThirdStreamStage`, `getChThird`, `getChThirdStarReward`, `getMusicReward`, `musicPointReview`, `playMusic`, `setChThirdChapterReward` |
| user | economy | 15 | `adViewLog`, `buyAvatar`, `buyCheck`, `buyItem`, `buyMusic`, `buyVarietyStore`, `checkBuyShop`, `paidEventPoint`, `setAdReward`, `setAttendance`, `setEventReward`, `setGameReward`, `setPassReward`, `setSelectReward`, `updateAchievement` |
| user | legacy-fallback | 37 | `MoreGamesLog`, `buyCollectionItem`, `buyCollectionMusic`, `buyExtraMode`, `buyPackage`, `buyPiece`, `buyUserTitle`, `challengeMissionList`, `changeUser`, `checkBuyProduct`, `checkPurchased`, `checkUser`, `deleteUser`, `facebookUserJoin`, `getAllPoint`, `getChoiceUser`, `getDiamondBonus`, `getProfileMusic`, `getPurchaseDiamondLog`, `getTransferId`, `getUserCollection`, `getUserInfo`, `getUserItemInven`, `itemPurchase`, `logCashComplete`, `setBookmark`, `setTutorial`, `setUserGP`, `transferUser`, `updateScore`, `useCoupon`, `useCredit`, `userAvatarList`, `userDel`, `userPurchase`, `userPurchaseErrorLog`, `userTitleList` |
| user | social | 4 | `setFollowerProfileGift`, `setFollowerQuestInfinite`, `setUserFollowerProfileReward`, `setUserFollowerQuest` |

Phân bố namespace: user78, main16, store8, music7, tour7, rank7, post5,
eventMode5, multi1. Năm tên đơn trùng namespace phải được xem riêng khi đổi routing.

Chi tiết DTO/owner/bootstrap từng dòng được test
`server/RpcLogicAuditTest.inventoryEveryWireCommandWithoutExecutingGameplay` sinh
ra `/tmp/opencode/rpc-logic-inventory.json` trong lượt audit. Test xác nhận đủ134
route,129tên, có Return DTO và encode/decode được envelope khung; không gọi
mutation cho toàn bộ134route chỉ để thử coverage.
