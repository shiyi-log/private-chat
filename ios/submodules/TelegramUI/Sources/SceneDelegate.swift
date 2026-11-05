import UIKit

/// Keeps the existing single-window AppDelegate initialization and event handlers.
@objc(SceneDelegate)
final class SceneDelegate: UIResponder, UIWindowSceneDelegate {
    var window: UIWindow?

    private var appDelegate: AppDelegate? {
        return UIApplication.shared.delegate as? AppDelegate
    }

    func scene(_ scene: UIScene, willConnectTo session: UISceneSession, options connectionOptions: UIScene.ConnectionOptions) {
        guard let windowScene = scene as? UIWindowScene, let window = self.appDelegate?.window else {
            return
        }
        self.window = window
        window.windowScene = windowScene
        window.frame = windowScene.coordinateSpace.bounds
        window.makeKeyAndVisible()

        self.scene(scene, openURLContexts: connectionOptions.urlContexts)
        for userActivity in connectionOptions.userActivities {
            self.scene(scene, continue: userActivity)
        }
        if let shortcutItem = connectionOptions.shortcutItem {
            self.windowScene(windowScene, performActionFor: shortcutItem, completionHandler: { _ in })
        }
    }

    func sceneDidBecomeActive(_ scene: UIScene) {
        self.appDelegate?.applicationDidBecomeActive(UIApplication.shared)
    }

    func sceneWillResignActive(_ scene: UIScene) {
        self.appDelegate?.applicationWillResignActive(UIApplication.shared)
    }

    func sceneWillEnterForeground(_ scene: UIScene) {
        self.appDelegate?.applicationWillEnterForeground(UIApplication.shared)
    }

    func sceneDidEnterBackground(_ scene: UIScene) {
        self.appDelegate?.applicationDidEnterBackground(UIApplication.shared)
    }

    func scene(_ scene: UIScene, openURLContexts URLContexts: Set<UIOpenURLContext>) {
        for context in URLContexts {
            var options: [UIApplication.OpenURLOptionsKey: Any] = [.openInPlace: context.options.openInPlace]
            if let sourceApplication = context.options.sourceApplication {
                options[.sourceApplication] = sourceApplication
            }
            if let annotation = context.options.annotation {
                options[.annotation] = annotation
            }
            let _ = self.appDelegate?.application(UIApplication.shared, open: context.url, options: options)
        }
    }

    func scene(_ scene: UIScene, continue userActivity: NSUserActivity) {
        let _ = self.appDelegate?.application(UIApplication.shared, continue: userActivity, restorationHandler: { _ in })
    }

    func windowScene(_ windowScene: UIWindowScene, performActionFor shortcutItem: UIApplicationShortcutItem, completionHandler: @escaping (Bool) -> Void) {
        guard let appDelegate = self.appDelegate else {
            completionHandler(false)
            return
        }
        appDelegate.application(UIApplication.shared, performActionFor: shortcutItem, completionHandler: completionHandler)
    }

    @available(iOS 26.0, *)
    func preferredWindowingControlStyle(for windowScene: UIWindowScene) -> UIWindowScene.WindowingControlStyle {
        return .minimal
    }
}
