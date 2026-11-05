package org.telegram.messenger;

import com.huawei.hms.push.HmsMessageService;
import com.huawei.hms.push.RemoteMessage;

import java.util.Map;

public class HuaweiPushListenerService extends HmsMessageService {
    @Override
    public void onMessageReceived(RemoteMessage remoteMessage) {
        if (!BuildVars.PUSH_SERVICES_ENABLED) {
            if (BuildVars.LOGS_ENABLED) {
                FileLog.d("HCM message ignored because push services are disabled.");
            }
            return;
        }
        Utilities.globalQueue.postRunnable(() -> {
            String from = remoteMessage.getFrom();
            String data = remoteMessage.getData();
            long time = remoteMessage.getSentTime();

            if (BuildVars.LOGS_ENABLED) {
                FileLog.d("HCM received data: " + data + " from: " + from);
            }

            PushListenerController.processRemoteMessage(PushListenerController.PUSH_TYPE_HUAWEI, data, time);
        });
    }

    @Override
    public void onNewToken(String token) {
        if (!BuildVars.PUSH_SERVICES_ENABLED) {
            if (BuildVars.LOGS_ENABLED) {
                FileLog.d("HCM token ignored because push services are disabled.");
            }
            SharedConfig.pushStringStatus = "__PRIVATE_PUSH_DISABLED__";
            PushListenerController.sendRegistrationToServer(PushListenerController.PUSH_TYPE_HUAWEI, null);
            return;
        }
        AndroidUtilities.runOnUIThread(() -> {
            if (BuildVars.LOGS_ENABLED) {
                FileLog.d("Refreshed HCM token: " + token);
            }
            ApplicationLoader.postInitApplication();
            PushListenerController.sendRegistrationToServer(PushListenerController.PUSH_TYPE_HUAWEI, token);
        });
    }
}
