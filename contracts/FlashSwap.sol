// SPDX-License-Identifier: UNLICENSED

pragma solidity >=0.6.6 <0.8.0;

import "../interfaces/IUniswapV2Router02.sol";
import "../interfaces/IUniswapV2Pair.sol";
import "../interfaces/IUniswapV2Factory.sol";
import "../interfaces/IERC20.sol";
import "../library/LowGasSafeMath.sol";

contract FlashSwap {
    address public owner;
    using LowGasSafeMath for uint256;
    using LowGasSafeMath for int256;

    constructor() public {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner);
        _;
    }

    function start(
        uint256 _maxBlockNumber,
        address _pairAddress,
        address _tokenBorrow, // example BUSD
        uint256 _tokenBorrowAmount, // example: BUSD => 10 * 1e18 [Amountout]
        address _sourceRouter,
        address _targetRouter
    ) public onlyOwner {
        require(block.number <= _maxBlockNumber, "out of block");

        address token0 = IUniswapV2Pair(_pairAddress).token0();
        address token1 = IUniswapV2Pair(_pairAddress).token1();

        require(
            token0 != address(0) && token1 != address(0),
            "token0 / token1 does not exist"
        );

        IUniswapV2Pair(_pairAddress).swap(
            _tokenBorrow == token0 ? _tokenBorrowAmount : 0,
            _tokenBorrow == token1 ? _tokenBorrowAmount : 0,
            address(this),
            abi.encode(_sourceRouter, _targetRouter)
        );
    }

    function execute(
        address _sender,
        uint256 _amount0,
        uint256 _amount1,
        bytes memory _data
    ) public {
        // obtain an amount of token that you exchanged
        uint256 amountToken = _amount0 == 0 ? _amount1 : _amount0;

        require(_sender == address(this), "unauthorized");

        IUniswapV2Pair iUniswapV2Pair = IUniswapV2Pair(msg.sender);
        address token0 = iUniswapV2Pair.token0();
        address token1 = iUniswapV2Pair.token1();

        // if _amount0 is zero sell token1 for token0
        // else sell token0 for token1 as a result
        address[] memory path1 = new address[](2);
        address[] memory path = new address[](2);
        path[0] = path1[1] = _amount0 == 0 ? token1 : token0; // c&p
        path[1] = path1[0] = _amount0 == 0 ? token0 : token1; // c&p

        (address sourceRouter, address targetRouter) = abi.decode(
            _data,
            (address, address)
        );
        require(
            sourceRouter != address(0) && targetRouter != address(0),
            "src/target router empty"
        );

        // IERC20 token that we will sell for otherToken
        IERC20 token = IERC20(_amount0 == 0 ? token1 : token0);
        token.approve(targetRouter, amountToken);

        // calculate the amount of token how much input token should be reimbursed
        uint256 amountRequired = IUniswapV2Router02(sourceRouter).getAmountsIn(
            amountToken,
            path1
        )[0];

        // swap token and obtain equivalent otherToken amountRequired as a result
        uint256 amountReceived = IUniswapV2Router02(targetRouter)
            .swapExactTokensForTokens(
                amountToken,
                amountRequired, // we already now what we need at least for payback; get less is a fail; slippage can be done via - ((amountRequired * 19) / 981) + 1,
                path,
                address(this), // its a foreign call; from router but we need contract address also equal to "_sender"
                block.timestamp + 60
            )[1];

        // fail if we didn't get enough tokens
        require(amountReceived > amountRequired, "do not get enough tokens");

        IERC20 otherToken = IERC20(_amount0 == 0 ? token0 : token1);

        // transfer failing already have error message
        otherToken.transfer(msg.sender, amountRequired); // send back borrow
        otherToken.transfer(
            owner,
            LowGasSafeMath.sub(amountReceived, amountRequired)
        ); // our win
    }

    function uniswapV2Call(
        address _sender,
        uint256 _amount0,
        uint256 _amount1,
        bytes calldata _data
    ) external {
        execute(_sender, _amount0, _amount1, _data);
    }

    function swap_tokens(
        address router,
        uint256 amountToken,
        uint256 amountRequired,
        address[] memory path
    ) public onlyOwner {
        IUniswapV2Router02(router).swapExactTokensForTokens(
            amountToken,
            amountRequired, // we already now what we need at least for payback; get less is a fail; slippage can be done via - ((amountRequired * 19) / 981) + 1,
            path,
            address(this), // its a foreign call; from router but we need contract address also equal to "_sender"
            block.timestamp + 60
        )[1];
    }
}
