// Test-only QML module FoamyFakeIme: a FakeIme singleton that sends an item
// the input-method events an input method (fcitx, IBus) would, so an
// offscreen test can compose a preedit. QML has no way to send them, and the
// offscreen platform loads no input method. tests/test_text_runs.py builds
// it into a temporary directory (moc, g++, Qt 6 Quick headers).
#include <QtCore/QCoreApplication>
#include <QtGui/QInputMethodEvent>
#include <QtQml/qqml.h>
#include <QtQml/qqmlextensionplugin.h>
#include <QtQuick/QQuickItem>

class FakeIme : public QObject {
  Q_OBJECT
public:
  using QObject::QObject;
  // Composing: `preedit` shows at the cursor, nothing is committed yet.
  Q_INVOKABLE void compose(QQuickItem *target, const QString &preedit) {
    QList<QInputMethodEvent::Attribute> attributes;
    attributes << QInputMethodEvent::Attribute(QInputMethodEvent::Cursor, preedit.length(), 1);
    QInputMethodEvent event(preedit, attributes);
    send(target, event);
  }
  // Ends the composition, committing `text` ("" commits nothing).
  Q_INVOKABLE void commit(QQuickItem *target, const QString &text) {
    QInputMethodEvent event;
    event.setCommitString(text);
    send(target, event);
  }

private:
  static void send(QQuickItem *target, QInputMethodEvent &event) {
    if (target)
      QCoreApplication::sendEvent(target, &event);
  }
};

class FakeImePlugin : public QQmlExtensionPlugin {
  Q_OBJECT
  Q_PLUGIN_METADATA(IID QQmlExtensionInterface_iid)
public:
  void registerTypes(const char *uri) override {
    qmlRegisterSingletonType<FakeIme>(uri, 1, 0, "FakeIme", [](QQmlEngine *, QJSEngine *) -> QObject * { return new FakeIme; });
  }
};

#include "FakeIme.moc"
