package emu.leman.ggserver.game.social;

import emu.leman.ggserver.Services;
import java.nio.file.Path;
import java.util.*;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static emu.leman.ggserver.util.Json.*;
import static org.junit.jupiter.api.Assertions.*;

class MailboxPersistenceTest {
    @TempDir Path root;
    @Test void deletedTargetReceiptAndNotificationWatermarkSurviveActualReopen() {
        long id,time;
        var rewards=List.of(obj("i_RewardType",1,"i_RewardId",1,"d_RewardQuantity",10.0));
        try(Services s=new Services(root)) {
            var user=s.state.createUser("mail-test","mail-device");
            user.put("welcome_post_sent",true); s.state.saveUser(user);
            var posts=new SocialPosts(s);
            var post=posts.sendPost("mail-test",obj("vi","Xin chào","en","Hello"),"",rewards,1,false,"persist-target-1");
            id=lng(post.get("idx"));time=SocialPosts.notificationTime(post);
            user=s.state.getUser("mail-test"); posts.claim(user,id,0); posts.delete(user,id,0);
        }
        try(Services s=new Services(root)) {
            var posts=new SocialPosts(s);
            var same=posts.sendPost("mail-test",obj("en","Hello","vi","Xin chào"),"",rewards,1,false,"persist-target-1");
            assertEquals(id,lng(same.get("idx")));
            assertTrue(posts.getUserPosts(s.state.getUser("mail-test")).isEmpty());
            var next=posts.sendPost("mail-test","next","",List.of(),1,false);
            assertTrue(lng(next.get("idx"))>id);
            assertTrue(SocialPosts.notificationTime(next)>time);
        }
    }
    @Test void expiredBroadcastRequestIsNotResentAfterPruneAndReopen() {
        long id;
        try(Services s=new Services(root)) {
            var posts=new SocialPosts(s);
            id=lng(posts.sendPost(null,"old","",List.of(),1,false,"persist-broadcast-1").get("idx"));
            var broadcasts=list(read(root.resolve("broadcast_posts.json")));
            map(broadcasts.getFirst()).put("del_time",1);write(root.resolve("broadcast_posts.json"),broadcasts);
            posts.sendPost(null,"new","",List.of(),1,false);
        }
        try(Services s=new Services(root)) {
            assertEquals(id,lng(new SocialPosts(s).sendPost("all","old","",List.of(),1,false,"persist-broadcast-1").get("idx")));
            assertEquals(2,list(read(root.resolve("broadcast_posts.json"))).size());
        }
    }
}
