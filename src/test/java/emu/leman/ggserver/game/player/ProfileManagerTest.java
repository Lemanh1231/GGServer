package emu.leman.ggserver.game.player;

import emu.leman.ggserver.Services;
import java.nio.file.Path;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static emu.leman.ggserver.util.Json.*;
import static org.junit.jupiter.api.Assertions.*;

class ProfileManagerTest {
    @TempDir Path root;

    @Test void longLivedManagerLoadsFreshSnapshotsAndDoesNotOverwriteOtherFeatures() {
        try(Services services=new Services(root)) {
            services.state.createUser("account","phone","");
            Player player=new Player(services,"phone");
            ProfileManager profile=player.profile();
            assertSame(player,profile.player());
            profile.setNickname("First");

            Map<String,Object> latest=services.state.getUser("account");
            map(latest.get("userdata")).putAll(obj("u_cp",731,"u_candy",4.5,"u_nick","Changed elsewhere"));
            latest.put("pending_grants",obj("cookies",3));
            latest.put("user_music",new java.util.ArrayList<>(java.util.List.of(obj("i_id",777,"i_Level",8))));
            services.state.saveUser(latest);

            assertEquals("Changed elsewhere",profile.profile().get("u_nick"));
            profile.setAvatar(9);
            profile.setTitle(4);
            latest=services.state.getUser("account");
            assertEquals(731,lng(map(latest.get("userdata")).get("u_cp")));
            assertEquals(4.5,dbl(map(latest.get("userdata")).get("u_candy")));
            assertEquals(3,integer(map(latest.get("pending_grants")).get("cookies")));
            assertTrue(list(latest.get("user_music")).stream().anyMatch(raw -> integer(map(raw).get("i_id"))==777 && integer(map(raw).get("i_Level"))==8));
            assertEquals("Changed elsewhere",profile.profile().get("u_nick"));
        }
        try(Services reopened=new Services(root)) {
            Map<String,Object> profile=new Player(reopened,"phone").profile().profile();
            assertEquals("Changed elsewhere",profile.get("u_nick"));
            assertEquals(9,integer(profile.get("u_avatar")));
            assertEquals(4,integer(profile.get("u_title")));
        }
    }

    @Test void missingAccountRetainsLegacyDefaultsWithoutCreatingAnAccount() {
        try(Services services=new Services(root)) {
            ProfileManager profile=new Player(services,"missing").profile();
            profile.setNickname("ignored"); profile.setAvatar(8); profile.setTitle(4);
            assertNull(services.state.getUser("missing"));
            Map<String,Object> values=profile.profile();
            assertEquals("Guitarist",values.get("u_nick"));
            assertEquals("",values.get("u_id"));
            assertEquals("KR",values.get("u_country"));
            assertEquals(1,values.get("u_avatar"));
            assertEquals(1,values.get("u_title"));
            assertEquals(15,values.size());
        }
    }
}
