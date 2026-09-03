import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects
import SddmComponents 2.0

Item {
    id: root
    width: 1920
    height: 1080

    TextConstants { id: textConstants }

    // Palette shared with waybar / rofi / kitty.
    readonly property color accent:     "#c084fc"
    readonly property color fgBright:   "#ffffff"
    readonly property color fg:         "#c4b5fd"
    readonly property color fgDim:      "#8b84a8"
    readonly property color glass:      Qt.rgba(48 / 255, 30 / 255, 98 / 255, 0.35)
    readonly property color glassInput: Qt.rgba(1, 1, 1, 0.05)
    readonly property color borderCol:  Qt.rgba(192 / 255, 132 / 255, 252 / 255, 0.30)
    readonly property color nacarado:   "#e3ccff"
    readonly property color danger:     "#f87171"

    Image {
        id: wallpaper
        anchors.fill: parent
        source: config.background || "background.png"
        fillMode: Image.PreserveAspectCrop
        asynchronous: false
        visible: false
    }

    MultiEffect {
        anchors.fill: parent
        source: wallpaper
        blurEnabled: (config.blurRadius || 0) > 0
        blur: 1.0
        blurMax: Number(config.blurRadius || 0)
        autoPaddingEnabled: false
    }

    // Veil so the glass card keeps its contrast over any wallpaper.
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: Qt.rgba(12 / 255, 6 / 255, 28 / 255, Number(config.dimOpacity || 0.35)) }
            GradientStop { position: 1.0; color: Qt.rgba(24 / 255, 10 / 255, 48 / 255, Number(config.dimOpacity || 0.35) + 0.18) }
        }
    }

    // Clock
    ColumnLayout {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        anchors.topMargin: root.height * 0.10
        spacing: 2

        Label {
            Layout.alignment: Qt.AlignHCenter
            text: Qt.formatTime(clock.now, "HH:mm")
            color: root.fgBright
            font.pointSize: 56
            font.weight: Font.Light
            style: Text.Raised
            styleColor: Qt.rgba(12 / 255, 6 / 255, 28 / 255, 0.95)
        }
        Label {
            Layout.alignment: Qt.AlignHCenter
            text: Qt.formatDate(clock.now, "dddd, d MMMM")
            color: root.fg
            font.pointSize: 14
        }
    }

    QtObject {
        id: clock
        property var now: new Date()
    }
    Timer {
        interval: 1000; running: true; repeat: true
        onTriggered: clock.now = new Date()
    }

    // Login card
    Rectangle {
        id: card
        width: 380
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.verticalCenter: parent.verticalCenter
        anchors.verticalCenterOffset: root.height * 0.06
        height: cardLayout.implicitHeight + 40
        radius: 20
        border.width: 1
        border.color: root.borderCol
        gradient: Gradient {
            GradientStop { position: 0.0; color: Qt.rgba(227 / 255, 204 / 255, 255 / 255, 0.18) }
            GradientStop { position: 0.45; color: Qt.rgba(48 / 255, 30 / 255, 98 / 255, 0.34) }
            GradientStop { position: 1.0; color: Qt.rgba(30 / 255, 18 / 255, 64 / 255, 0.44) }
        }

        Rectangle {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.margins: 1
            height: 1
            radius: 1
            color: Qt.rgba(255, 255, 255, 0.35)
        }

        ColumnLayout {
            id: cardLayout
            anchors.fill: parent
            anchors.margins: 20
            spacing: 14

            // Avatar
            Rectangle {
                Layout.alignment: Qt.AlignHCenter
                Layout.preferredWidth: 84
                Layout.preferredHeight: 84
                radius: 42
                gradient: Gradient {
                    GradientStop { position: 0.0; color: Qt.rgba(227 / 255, 204 / 255, 255 / 255, 0.22) }
                    GradientStop { position: 1.0; color: Qt.rgba(124 / 255, 58 / 255, 237 / 255, 0.14) }
                }
                border.width: 1
                border.color: root.borderCol

                Image {
                    id: face
                    anchors.fill: parent
                    anchors.margins: 3
                    source: userList.currentIndex >= 0
                            ? (userModel.data(userModel.index(userList.currentIndex, 0), Qt.UserRole + 4) || "")
                            : ""
                    fillMode: Image.PreserveAspectCrop
                    visible: false
                }
                MultiEffect {
                    anchors.fill: face
                    source: face
                    maskEnabled: true
                    maskSource: mask
                    visible: face.status === Image.Ready
                }
                Item {
                    id: mask
                    anchors.fill: face
                    layer.enabled: true
                    visible: false
                    Rectangle { anchors.fill: parent; radius: width / 2; color: "white" }
                }
                Label {
                    anchors.centerIn: parent
                    visible: face.status !== Image.Ready
                    text: userList.currentText.length > 0 ? userList.currentText.charAt(0).toUpperCase() : "?"
                    color: root.accent
                    font.pointSize: 30
                }
            }

            // User selector
            ComboBox {
                id: userList
                Layout.fillWidth: true
                model: userModel
                textRole: "name"
                currentIndex: userModel.lastIndex
                font.pointSize: 11

                contentItem: Label {
                    leftPadding: 12
                    text: userList.currentText
                    color: root.fgBright
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideRight
                }
                background: Rectangle {
                    implicitHeight: 40
                    radius: 10
                    color: root.glassInput
                    border.width: 1
                    border.color: userList.activeFocus ? root.accent : root.borderCol
                }
                indicator: Label {
                    x: userList.width - width - 12
                    y: (userList.height - height) / 2
                    text: "▾"
                    color: root.fgDim
                }
                popup: Popup {
                    y: userList.height + 4
                    width: userList.width
                    implicitHeight: Math.min(contentItem.implicitHeight + 8, 220)
                    padding: 4
                    background: Rectangle {
                        radius: 10
                        color: Qt.rgba(46 / 255, 32 / 255, 82 / 255, 0.97)
                        border.width: 1
                        border.color: root.borderCol
                    }
                    contentItem: ListView {
                        clip: true
                        implicitHeight: contentHeight
                        model: userList.popup.visible ? userList.delegateModel : null
                        currentIndex: userList.highlightedIndex
                        ScrollIndicator.vertical: ScrollIndicator {}
                    }
                }
                delegate: ItemDelegate {
                    width: userList.width - 8
                    highlighted: userList.highlightedIndex === index
                    contentItem: Label {
                        text: model.name
                        color: root.fgBright
                        verticalAlignment: Text.AlignVCenter
                    }
                    background: Rectangle {
                        radius: 8
                        color: highlighted ? Qt.rgba(139 / 255, 92 / 255, 246 / 255, 0.32) : "transparent"
                    }
                }
            }

            // Password
            TextField {
                id: password
                Layout.fillWidth: true
                echoMode: TextInput.Password
                placeholderText: textConstants.password || "Contraseña"
                placeholderTextColor: root.fgDim
                color: root.fgBright
                font.pointSize: 11
                leftPadding: 12
                focus: true
                background: Rectangle {
                    implicitHeight: 40
                    radius: 10
                    color: root.glassInput
                    border.width: 1
                    border.color: password.activeFocus ? root.accent : root.borderCol
                }
                Keys.onReturnPressed: root.login()
                Keys.onEnterPressed: root.login()
            }

            // Login button
            Button {
                id: loginButton
                Layout.fillWidth: true
                text: textConstants.login || "Iniciar sesión"
                enabled: !root.busy
                onClicked: root.login()

                contentItem: Label {
                    text: loginButton.text
                    color: root.fgBright
                    font.pointSize: 11
                    font.weight: Font.DemiBold
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                background: Rectangle {
                    implicitHeight: 40
                    radius: 10
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: loginButton.down
                                                       ? Qt.rgba(124 / 255, 58 / 255, 237 / 255, 0.75)
                                                       : (loginButton.hovered ? Qt.rgba(167 / 255, 139 / 255, 250 / 255, 0.62)
                                                                              : Qt.rgba(167 / 255, 139 / 255, 250 / 255, 0.40)) }
                        GradientStop { position: 1.0; color: loginButton.down
                                                       ? Qt.rgba(76 / 255, 29 / 255, 149 / 255, 0.80)
                                                       : (loginButton.hovered ? Qt.rgba(124 / 255, 58 / 255, 237 / 255, 0.66)
                                                                              : Qt.rgba(124 / 255, 58 / 255, 237 / 255, 0.44)) }
                    }
                    border.width: 1
                    border.color: loginButton.hovered ? root.nacarado : root.borderCol
                    Behavior on border.color { ColorAnimation { duration: 150 } }
                }
            }

            Label {
                id: message
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                color: root.danger
                font.pointSize: 10
                wrapMode: Text.WordWrap
                text: ""
            }
        }
    }

    // Session + power bar
    RowLayout {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 32
        spacing: 10

        ComboBox {
            id: sessionList
            model: sessionModel
            textRole: "name"
            currentIndex: sessionModel.lastIndex
            implicitWidth: 220
            font.pointSize: 10

            contentItem: Label {
                leftPadding: 12
                text: sessionList.currentText
                color: root.fg
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }
            background: Rectangle {
                implicitHeight: 34
                radius: 9
                color: Qt.rgba(179 / 255, 157 / 255, 219 / 255, 0.16)
                border.width: 1
                border.color: root.borderCol
            }
            indicator: Label {
                x: sessionList.width - width - 12
                y: (sessionList.height - height) / 2
                text: "▾"
                color: root.fgDim
            }
            popup: Popup {
                y: -implicitHeight - 4
                width: sessionList.width
                implicitHeight: Math.min(contentItem.implicitHeight + 8, 220)
                padding: 4
                background: Rectangle {
                    radius: 10
                    color: Qt.rgba(46 / 255, 32 / 255, 82 / 255, 0.97)
                    border.width: 1
                    border.color: root.borderCol
                }
                contentItem: ListView {
                    clip: true
                    implicitHeight: contentHeight
                    model: sessionList.popup.visible ? sessionList.delegateModel : null
                    currentIndex: sessionList.highlightedIndex
                    ScrollIndicator.vertical: ScrollIndicator {}
                }
            }
            delegate: ItemDelegate {
                width: sessionList.width - 8
                highlighted: sessionList.highlightedIndex === index
                contentItem: Label {
                    text: model.name
                    color: root.fgBright
                    verticalAlignment: Text.AlignVCenter
                }
                background: Rectangle {
                    radius: 8
                    color: highlighted ? Qt.rgba(139 / 255, 92 / 255, 246 / 255, 0.32) : "transparent"
                }
            }
        }

        Component {
            id: powerButton
            Button {
                id: powerBtn
                property string glyph: ""
                property color hoverColor: root.accent
                implicitWidth: 40
                implicitHeight: 34
                contentItem: Label {
                    text: powerBtn.glyph
                    color: powerBtn.hovered ? powerBtn.hoverColor : root.fg
                    font.pointSize: 13
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                background: Rectangle {
                    radius: 9
                    color: Qt.rgba(179 / 255, 157 / 255, 219 / 255, powerBtn.hovered ? 0.30 : 0.16)
                    border.width: 1
                    border.color: root.borderCol
                    Behavior on color { ColorAnimation { duration: 150 } }
                }
            }
        }

        Loader {
            sourceComponent: powerButton
            onLoaded: {
                item.glyph = "↻"
                item.clicked.connect(function () { sddm.reboot() })
            }
        }
        Loader {
            sourceComponent: powerButton
            onLoaded: {
                item.glyph = "⏻"
                item.hoverColor = root.danger
                item.clicked.connect(function () { sddm.powerOff() })
            }
        }
    }

    property bool busy: false

    function login() {
        if (root.busy)
            return
        root.busy = true
        message.text = ""
        sddm.login(userList.currentText, password.text, sessionList.currentIndex)
    }

    Connections {
        target: sddm
        function onLoginFailed() {
            root.busy = false
            message.text = textConstants.loginFailed || "Usuario o contraseña incorrectos"
            password.text = ""
            password.forceActiveFocus()
        }
        function onLoginSucceeded() {
            root.busy = false
        }
    }

    Component.onCompleted: password.forceActiveFocus()
}
