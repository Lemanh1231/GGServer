package com.kotori.guitargirl.network;

import android.content.ContentProvider;
import android.content.ContentValues;
import android.content.Context;
import android.content.SharedPreferences;
import android.database.Cursor;
import android.net.Uri;
import android.util.Log;

/**
 * Auto-starting ContentProvider invoked by Android OS before Application.onCreate()
 * and before any Activity or Unity IL2CPP library loads.
 *
 * Class name is intentionally 59 chars to match PlayGamesInitProvider in-place inside AXML.
 */
public final class MultiDomainFailoverProviderV1 extends ContentProvider {

    private static final String TAG = "GGFailover";
    private static final String PREF_NAME = "gg_multidomain_failover";
    private static final String KEY_ACTIVE_IDX = "active_domain_idx";

    @Override
    public boolean onCreate() {
        final Context ctx = getContext();
        DomainFailoverGateway.ensureStarted(new DomainFailoverGateway.StateStore() {
            @Override
            public int loadActiveIndex() {
                if (ctx == null) {
                    return 0;
                }
                SharedPreferences sp = ctx.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE);
                return sp.getInt(KEY_ACTIVE_IDX, 0);
            }

            @Override
            public void saveActiveIndex(int index) {
                if (ctx == null) {
                    return;
                }
                SharedPreferences sp = ctx.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE);
                sp.edit().putInt(KEY_ACTIVE_IDX, index).apply();
            }

            @Override
            public void logInfo(String msg) {
                Log.i(TAG, msg);
            }

            @Override
            public void logWarn(String msg) {
                Log.w(TAG, msg);
            }
        });
        return true;
    }

    @Override
    public Cursor query(Uri uri, String[] projection, String selection, String[] selectionArgs, String sortOrder) {
        return null;
    }

    @Override
    public String getType(Uri uri) {
        return null;
    }

    @Override
    public Uri insert(Uri uri, ContentValues values) {
        return null;
    }

    @Override
    public int delete(Uri uri, String selection, String[] selectionArgs) {
        return 0;
    }

    @Override
    public int update(Uri uri, ContentValues values, String selection, String[] selectionArgs) {
        return 0;
    }
}
