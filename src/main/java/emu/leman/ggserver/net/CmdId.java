package emu.leman.ggserver.net;

import java.util.Map;
import java.util.Set;

/** Guitar Girl command IDs. Values are client wire strings, not Nebula numeric IDs.
 * Schema-only commands remain eligible for the legacy fallback, not registered handlers.
 */
public final class CmdId {
    private CmdId() {}

    public static final String MORE_GAMES_LOG = "MoreGamesLog";
    public static final String REQUEST = "Request";
    public static final String AD_VIEW_LOG = "adViewLog";
    public static final String AVATAR_LIST = "avatarList";
    public static final String BUY_AVATAR = "buyAvatar";
    public static final String BUY_CHECK = "buyCheck";
    public static final String BUY_COLLECTION_ITEM = "buyCollectionItem";
    public static final String BUY_COLLECTION_MUSIC = "buyCollectionMusic";
    public static final String BUY_CONTENTS = "buyContents";
    public static final String BUY_EXTRA_MODE = "buyExtraMode";
    public static final String BUY_ITEM = "buyItem";
    public static final String BUY_MUSIC = "buyMusic";
    public static final String BUY_PACKAGE = "buyPackage";
    public static final String BUY_PIECE = "buyPiece";
    public static final String BUY_SHOP = "buyShop";
    public static final String BUY_USER_TITLE = "buyUserTitle";
    public static final String BUY_VARIETY_STORE = "buyVarietyStore";
    public static final String CH_THIRD_STAGE = "chThirdStage";
    public static final String CH_THIRD_STREAM_STAGE = "chThirdStreamStage";
    public static final String CHALLENGE_MISSION_LIST = "challengeMissionList";
    public static final String CHANGE_USER = "changeUser";
    public static final String CHECK_BUY_PRODUCT = "checkBuyProduct";
    public static final String CHECK_BUY_SHOP = "checkBuyShop";
    public static final String CHECK_PURCHASED = "checkPurchased";
    public static final String CHECK_USER = "checkUser";
    public static final String COMPLETE_LOG = "completeLog";
    public static final String DEFAULT_SETTING_LIST = "defaultSettingList";
    public static final String DELETE_POST = "deletePost";
    public static final String DELETE_USER = "deleteUser";
    public static final String END_PLAY_MUSIC = "endPlayMusic";
    public static final String EVENT_REWARD_LIST = "eventRewardList";
    public static final String FACEBOOK_USER_JOIN = "facebookUserJoin";
    public static final String GET_ALBUM = "getAlbum";
    public static final String GET_ALBUM_INFO_LIST = "getAlbumInfoList";
    public static final String GET_ALBUM_LIST = "getAlbumList";
    public static final String GET_ALL_POINT = "getAllPoint";
    public static final String GET_CACHE = "getCache";
    public static final String GET_CH_THIRD = "getChThird";
    public static final String GET_CH_THIRD_STAR_REWARD = "getChThirdStarReward";
    public static final String GET_CHOICE_USER = "getChoiceUser";
    public static final String GET_COLLECTION = "getCollection";
    public static final String GET_COUNTRY_MY_RANK = "getCountryMyRank";
    public static final String GET_COUNTRY_RANK = "getCountryRank";
    public static final String GET_DIAMOND_BONUS = "getDiamondBonus";
    public static final String GET_EVENT_MAIN = "getEventMain";
    public static final String GET_EVENT_RANK = "getEventRank";
    public static final String GET_EVENT_REWARD_LIST = "getEventRewardList";
    public static final String GET_GAME_DATA_LIST = "getGameDataList";
    public static final String GET_LOCAL_PUSH = "getLocalPush";
    public static final String GET_MASTERS_RANK = "getMastersRank";
    public static final String GET_MUSIC_INFO_LIST = "getMusicInfoList";
    public static final String GET_MUSIC_LIST = "getMusicList";
    public static final String GET_MUSIC_RANK = "getMusicRank";
    public static final String GET_MUSIC_REWARD = "getMusicReward";
    public static final String GET_NOTICE_LIST = "getNoticeList";
    public static final String GET_POST = "getPost";
    public static final String GET_POST_TIME = "getPostTime";
    public static final String GET_PROFILE = "getProfile";
    public static final String GET_PROFILE_MUSIC = "getProfileMusic";
    public static final String GET_PURCHASE_DIAMOND_LOG = "getPurchaseDiamondLog";
    public static final String GET_RANK_MAIN = "getRankMain";
    public static final String GET_REVIEW_POINT = "getReviewPoint";
    public static final String GET_SAM_SECK_LIST = "getSamSeckList";
    public static final String GET_SAM_SECK_REWARD = "getSamSeckReward";
    public static final String GET_SERVER_LIST = "getServerList";
    public static final String GET_SERVER_TIME = "getServerTime";
    public static final String GET_TAB_LIST = "getTabList";
    public static final String GET_TOTAL_COUNTRY_RANK = "getTotalCountryRank";
    public static final String GET_TOTAL_MUSIC_RANK = "getTotalMusicRank";
    public static final String GET_TOUR_LIST = "getTourList";
    public static final String GET_TOUR_RANK = "getTourRank";
    public static final String GET_TRANSFER_ID = "getTransferId";
    public static final String GET_UPDATE_TIME = "getUpdateTime";
    public static final String GET_USER_COLLECTION = "getUserCollection";
    public static final String GET_USER_INFO = "getUserInfo";
    public static final String GET_USER_ITEM_INVEN = "getUserItemInven";
    public static final String GET_VARIETY_STORE = "getVarietyStore";
    public static final String HIBERNATION_LOG = "hibernationLog";
    public static final String ITEM_PURCHASE = "itemPurchase";
    public static final String ITEM_STORE_LIST = "itemStoreList";
    public static final String LAST_SAVE_TIME = "lastSaveTime";
    public static final String LOG_CASH_COMPLETE = "logCashComplete";
    public static final String MAIN = "main";
    public static final String MORE_GAMES = "moreGames";
    public static final String MUSIC_POINT_REVIEW = "musicPointReview";
    public static final String NEW_STORE_LIST = "newStoreList";
    public static final String PAID_EVENT_POINT = "paidEventPoint";
    public static final String PLAY_CHECK = "playCheck";
    public static final String PLAY_MUSIC = "playMusic";
    public static final String PROVIDE_POST = "providePost";
    public static final String READ_POST = "readPost";
    public static final String SET_AD_REWARD = "setAdReward";
    public static final String SET_ATTENDANCE = "setAttendance";
    public static final String SET_BOOKMARK = "setBookmark";
    public static final String SET_CH_THIRD_CHAPTER_REWARD = "setChThirdChapterReward";
    public static final String SET_EVENT_REWARD = "setEventReward";
    public static final String SET_FOLLOWER_PROFILE_GIFT = "setFollowerProfileGift";
    public static final String SET_FOLLOWER_QUEST_INFINITE = "setFollowerQuestInfinite";
    public static final String SET_GAME_REWARD = "setGameReward";
    public static final String SET_PASS_REWARD = "setPassReward";
    public static final String SET_REVIEW_POPUP = "setReviewPopup";
    public static final String SET_SELECT_REWARD = "setSelectReward";
    public static final String SET_SUBSCRIBE = "setSubscribe";
    public static final String SET_TUTORIAL = "setTutorial";
    public static final String SET_TUTORIAL_NEW = "setTutorialNew";
    public static final String SET_USER_FOLLOWER_PROFILE_REWARD = "setUserFollowerProfileReward";
    public static final String SET_USER_FOLLOWER_QUEST = "setUserFollowerQuest";
    public static final String SET_USER_GP = "setUserGP";
    public static final String STORE_LIST = "storeList";
    public static final String STORE_NOTICE = "storeNotice";
    public static final String TITLE_LIST = "titleList";
    public static final String TOUR_MAIN = "tourMain";
    public static final String TRANSFER_USER = "transferUser";
    public static final String UPDATE_ACHIEVEMENT = "updateAchievement";
    public static final String UPDATE_AVATAR = "updateAvatar";
    public static final String UPDATE_NICK_NAME = "updateNickName";
    public static final String UPDATE_SCORE = "updateScore";
    public static final String UPDATE_USER_TITLE = "updateUserTitle";
    public static final String USE_COUPON = "useCoupon";
    public static final String USE_CREDIT = "useCredit";
    public static final String USER_AVATAR_LIST = "userAvatarList";
    public static final String USER_DEL = "userDel";
    public static final String USER_JOIN = "userJoin";
    public static final String USER_LOAD = "userLoad";
    public static final String USER_LOGIN = "userLogin";
    public static final String USER_PURCHASE = "userPurchase";
    public static final String USER_PURCHASE_ERROR_LOG = "userPurchaseErrorLog";
    public static final String USER_SAVE = "userSave";
    public static final String USER_TITLE_LIST = "userTitleList";

    /** Full schema names, since HTTP bootstrap bypasses session authentication. */
    public static final Set<String> BOOTSTRAP = Set.of("main."+REQUEST,
            "main."+GET_SERVER_TIME,"main."+GET_UPDATE_TIME,"main."+DEFAULT_SETTING_LIST,
            "main."+GET_GAME_DATA_LIST,"store."+GET_VARIETY_STORE);

    /** Exceptions to the usual command + Return convention. */
    public static final Map<String,String> SPECIAL_RETURNS = Map.of(
            REQUEST,"initReturn",FACEBOOK_USER_JOIN,USER_JOIN+"Return",
            SET_CH_THIRD_CHAPTER_REWARD,GET_CH_THIRD_STAR_REWARD+"Return");
}
