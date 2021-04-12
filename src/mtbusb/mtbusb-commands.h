#ifndef MTBUSB_COMMANDS
#define MTBUSB_COMMANDS

/*
This file defines MTB-USB & MTBbus commands.
Each command type has its own class inherited from Cmd.
See mtbusb.h or README for more documentation.
*/

#include <functional>
#include "mtbusb-common.h"

namespace Mtb {

using StdCallbackFunc = std::function<void(void *data)>;

template <typename F>
struct CommandCallback {
	F const func;
	void *const data;

	CommandCallback()
	    : func([](void*) {}), data(nullptr) {}
	CommandCallback(F const func, void *const data = nullptr)
	    : func(func), data(data) {}
};

struct Cmd {
	const CommandCallback<StdCallbackFunc> onError;

	Cmd(const CommandCallback<StdCallbackFunc>& onError = {}) : onError(onError) {}
	virtual std::vector<uint8_t> getBytes() const = 0;
	virtual QString msg() const = 0;
	virtual ~Cmd() = default;
	virtual bool conflict(const Cmd &) const { return false; }
	virtual bool processResponse(uint8_t usbCommandCode, std::vector<uint8_t> data) const = 0;
		// returns true iff response processed
	virtual void callError() const {
		if (nullptr != onError.func)
			onError.func(onError.data);
	}
};

template <typename Target>
bool is(const Cmd &x) {
	return (dynamic_cast<const Target *>(&x) != nullptr);
}

/* MTB-USB commands ----------------------------------------------------------*/

struct CmdMtbUsbInfoRequest : public Cmd {
	const CommandCallback<StdCallbackFunc> onOk; // no special callback here, data could be read from MtbUsb class directly

	CmdMtbUsbInfoRequest(const CommandCallback<StdCallbackFunc>& onOk = {},
	                     const CommandCallback<StdCallbackFunc>& onError = {})
	 : Cmd(onError), onOk(onOk) {}

	std::vector<uint8_t> getBytes() const override { return {0x20}; }
	QString msg() const override { return "MTB-USB Information Request"; }

	bool processResponse(uint8_t usbCommandCode, std::vector<uint8_t> data) const override {
		return true;
	}
};

struct CmdMtbUsbChangeSpeed : public Cmd {
	const MtbBusSpeed speed;
	const CommandCallback<StdCallbackFunc> onOk;

	CmdMtbUsbChangeSpeed(const MtbBusSpeed speed, const CommandCallback<StdCallbackFunc>& onOk = {},
	                     const CommandCallback<StdCallbackFunc>& onError = {})
	  : Cmd(onError), speed(speed), onOk(onOk) {}

	std::vector<uint8_t> getBytes() const override {
		return {0x21, static_cast<uint8_t>(speed)};
	}
	QString msg() const override {
		return "MTB-USB Change MTBbus Speed to "+QString(mtbBusSpeedToInt(speed))+" baud/s";
	}
	bool conflict(const Cmd &cmd) const override { return is<CmdMtbUsbChangeSpeed>(cmd); }
};

struct CmdMtbUsbActiveModulesRequest : public Cmd {
	std::vector<uint8_t> getBytes() const override { return {0x22}; }
	QString msg() const override { return "MTB-USB Active Modules Requst"; }
};

struct CmdMtbUsbForward : public Cmd {
	static constexpr uint8_t usbCommandCode = 0x10;
	const uint8_t module;

	CmdMtbUsbForward(uint8_t module, const CommandCallback<StdCallbackFunc>& onError = {})
	 : Cmd(onError), module(module) {
		if (module == 0)
			throw EInvalidAddress(module);
	}
};

/* MTBbus commands -----------------------------------------------------------*/

struct ModuleInfo {
	uint8_t type;
	bool bootloader_int;
	bool bootloader_unint;
	uint8_t fw_major;
	uint8_t fw_minor;
	uint8_t proto_major;
	uint8_t proto_minor;
};

using ModuleInfoCallbackFunc = std::function<void(ModuleInfo info, void *data)>;

struct CmdMtbModuleInfoRequest : public CmdMtbUsbForward {
	const CommandCallback<ModuleInfoCallbackFunc> onInfo;

	CmdMtbModuleInfoRequest(uint8_t module, const CommandCallback<ModuleInfoCallbackFunc> onInfo,
	                        const CommandCallback<StdCallbackFunc> onError)
	 : CmdMtbUsbForward(module, onError), onInfo(onInfo) {}
	std::vector<uint8_t> getBytes() const override { return {usbCommandCode, module, 0x20}; }
	QString msg() const override { return "Module "+QString(module)+" Information Request"; }
};

}; // namespace Mtb

#endif