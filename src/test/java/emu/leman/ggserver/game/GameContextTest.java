package emu.leman.ggserver.game;

import emu.leman.ggserver.game.account.AccountModule;

import emu.leman.ggserver.Services;
import java.nio.file.Path;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;

class GameContextTest {
    @TempDir Path root;

    @Test void bootstrapsLegacyCommandsPlusExplicitLocalPushListAndInventoriesActualOwnership() {
        try(Services services=new Services(root)) {
            GameContext context=new GameContext(services).registerModules();
            Map<String,Set<String>> expected=Map.of(
                "auth",Set.of("userJoin","userLogin","userSave","userLoad","lastSaveTime","setTutorialNew","setSubscribe","setReviewPopup","updateNickName","updateAvatar","updateUserTitle","getProfile","Request","getServerTime","getUpdateTime","defaultSettingList","hibernationLog","getLocalPush","completeLog"),
                "economy",Set.of("buyVarietyStore","buyCheck","checkBuyShop","buyShop","buyMusic","buyAvatar","buyItem","buyContents","setAttendance","getEventRewardList","setEventReward","setSelectReward","setGameReward","updateAchievement","setPassReward","setAdReward","adViewLog","paidEventPoint"),
                "social",Set.of("setFollowerProfileGift","setUserFollowerProfileReward","setFollowerQuestInfinite","setUserFollowerQuest","getPostTime","getPost","providePost","readPost","deletePost"),
                "content",Set.of("getGameDataList","getVarietyStore","getSamSeckList","getSamSeckReward","getEventMain","getEventRank","eventRewardList","getChThird","chThirdStage","chThirdStreamStage","getChThirdStarReward","setChThirdChapterReward","playMusic","musicPointReview","getMusicReward"));
            assertEquals(expected,context.commands());
            assertEquals(expected.keySet(),context.modules().keySet());
            Set<String> all=new HashSet<>(); expected.values().forEach(all::addAll);
            assertEquals(61,all.size());
            assertEquals(all,services.registry.commands());
            assertSame(context,context.registerModules());
            assertEquals(expected,context.commands());
            assertThrows(UnsupportedOperationException.class,() -> context.modules().clear());
            assertThrows(UnsupportedOperationException.class,() -> context.commands().get("auth").clear());
        }
    }

    @Test void rejectsDuplicateModuleIdsAndCanInstallAnAdditionalRealModule() {
        try(Services services=new Services(root)) {
            GameContext context=new GameContext(services);
            assertThrows(IllegalStateException.class,() -> context.addModule(new AccountModule(services)));
            context.addModule(new GameModule() {
                @Override public String id() { return "test-feature"; }
                @Override public void register() { services.registry.register("testCommand",(r,c) -> emu.leman.ggserver.net.Result.ok("test")); }
            }).registerModules();
            assertEquals(Set.of("testCommand"),context.commands().get("test-feature"));
            assertEquals(62,services.registry.commands().size());
        }
    }
}
