package emu.leman.ggserver.net;

import emu.leman.ggserver.Services;
import emu.leman.ggserver.game.account.AuthApi;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static emu.leman.ggserver.util.Json.*;
import static org.junit.jupiter.api.Assertions.*;

class AuthApiSessionTest {
    @TempDir Path root;
    @Test void failedProfileLookupMustNotIssueASessionForAnUnresolvedAccount() {
        try(Services services=new Services(root)) {
            services.state.close();
            assertThrows(IllegalStateException.class,()->new AuthApi(services).login(obj("device_cd","phone")));
            assertEquals(0,services.sessions.sessionCount());
        }
    }

    @Test void blankDevicePreservesLegacyBootstrapMemberAndJsonSchema() {
        try(Services services=new Services(root)) {
            var response=new AuthApi(services).handle("/api/accounts/v3/global/login?unused=1",obj());
            assertEquals("application/json; charset=utf-8",response.contentType());
            var envelope=map(parse(new String(response.body(),StandardCharsets.UTF_8)));
            assertEquals(Set.of("value","result_code","result_msg"),envelope.keySet());
            assertEquals("000",envelope.get("result_code"));
            assertEquals("API_OK",envelope.get("result_msg"));
            var value=map(envelope.get("value"));
            assertEquals(Set.of("access_token","member","force_receipt","conflict_member_id","is_guest_login",
                    "old_member_id","jailbreak_yn","fcm_send_lang","unreg_status","unreg_remain_time","callTime"),value.keySet());
            var member=map(value.get("member"));
            assertEquals(Set.of("crt_dt","upd_dt","status_cd","member_id","nickname","profile_img_url","feeling",
                    "adult_auth_yn","adult_auth_dt","recent_login_dt","recent_app_id","email","anonymous_yn",
                    "friend_accept_cd","reg_path","recent_app_title","last_msg_dt","new_msg_yn","conflict_member_id",
                    "reg_ip","reg_nation","is_guest_login","provider_display_name","pushgroup","locale"),member.keySet());
            assertEquals(429071553,lng(member.get("member_id")));
            assertEquals("Guitarist",member.get("nickname"));
            assertEquals("PmangPlus",member.get("provider_display_name"));
            String token=str(value.get("access_token"));
            assertTrue(token.startsWith("429071553|0||KR|"));
            assertNotNull(services.sessions.find(token));
        }
    }

    @Test void repeatedLoginResolvesCanonicalAliasAndDoesNotCacheMutableUserState() {
        try(Services services=new Services(root)) {
            var user=services.state.createUser("canonical-account","phone","");
            long memberId=lng(map(user.get("userdata")).get("u_seq"));
            AuthApi auth=new AuthApi(services);
            var first=map(auth.login(obj("device_cd","phone","app_id","123","access_token","client-chosen"),"203.0.113.1").get("value"));
            map(user.get("userdata")).put("u_nick","Changed nickname");
            services.state.saveUser(user);
            var second=map(auth.login(obj("device_cd","phone","app_id","123"),"203.0.113.2").get("value"));
            String firstToken=str(first.get("access_token")), secondToken=str(second.get("access_token"));
            assertNotEquals(firstToken,secondToken);
            assertTrue(firstToken.contains("|123|phone|KR|"));
            assertEquals(memberId,lng(map(second.get("member")).get("member_id")));
            assertEquals("Changed nickname",map(second.get("member")).get("nickname"));
            Session firstSession=services.sessions.find(firstToken), secondSession=services.sessions.find(secondToken);
            assertEquals("canonical-account",firstSession.canonicalUuid());
            assertEquals("canonical-account",secondSession.canonicalUuid());
            assertEquals("phone",firstSession.deviceUuid());
            assertEquals("203.0.113.1",firstSession.ip());
            assertEquals("203.0.113.2",secondSession.ip());
            assertNull(services.sessions.find("client-chosen"));
            assertEquals(2,services.sessions.sessionCount());
            services.sessions.invalidate(firstToken);
            assertSame(secondSession,services.sessions.find(secondToken));
            assertNotNull(services.state.getUser("canonical-account"));
        }
    }

    @Test void separateAccountsNeverShareTokensAndServicesCloseRevokesThem() {
        Services services=new Services(root);
        String firstToken,secondToken;
        try {
            AuthApi auth=new AuthApi(services);
            firstToken=str(map(auth.login(obj("device_cd","one")).get("value")).get("access_token"));
            secondToken=str(map(auth.login(obj("device_cd","two")).get("value")).get("access_token"));
            assertEquals("one",services.sessions.find(firstToken).canonicalUuid());
            assertEquals("two",services.sessions.find(secondToken).canonicalUuid());
            assertNotEquals(firstToken,secondToken);
        } finally { services.close(); }
        assertEquals(0,services.sessions.sessionCount());
    }
}
